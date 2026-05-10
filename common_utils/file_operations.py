"""
File operations service for handling CSV file uploads, deletions, and operations.

This service provides thread-safe file operations with proper locking mechanisms
to prevent race conditions when multiple operations are performed on the same files.
"""

import asyncio
import os
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from aiorwlock import RWLock
from fastapi import HTTPException, UploadFile

from common_utils.logger import get_logger
from common_utils.models import FileDeleteResponse, UploadResponse

logger = get_logger(__name__)


class FileOperationsService:
    """
    Service for handling file operations with thread-safe locking.

    This service provides methods for uploading, deleting, and managing CSV files
    with proper read-write locking to prevent race conditions.
    """

    def __init__(self):
        """Initialize the file operations service."""
        # Dictionary to store file-specific read-write locks
        self._file_rw_locks: Dict[str, RWLock] = defaultdict(RWLock)

    def _get_file_rw_lock(self, file_path: str) -> RWLock:
        """
        Get or create a read-write lock for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            RWLock instance for the file
        """
        # #region agent log
        result = self._file_rw_locks[file_path]
        try:
            from common_utils.metrics import track_metric_sync

            track_metric_sync(
                "app",
                "gauge",
                "file_operations_lock_dict_size",
                len(self._file_rw_locks),
                None,
            )
        except Exception:
            pass
        # #endregion
        return result

    async def cleanup_data_folder(self) -> None:
        """Clean up all files in the data folder."""
        data_path = Path("data")
        if data_path.exists():
            try:
                # Remove all contents of the data folder (run in thread to avoid blocking)
                await asyncio.to_thread(shutil.rmtree, data_path)
                # Recreate the empty data folder (run in thread to avoid blocking)
                await asyncio.to_thread(data_path.mkdir, parents=True, exist_ok=True)
                logger.info("Data folder cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up data folder: {str(e)}")
                raise

    async def check_file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists at the given path with proper locking.

        Args:
            file_path: Path to the file to check

        Returns:
            True if file exists, False otherwise
        """
        # Use file-specific read lock to allow multiple readers
        async with self._get_file_rw_lock(file_path).reader:
            return await asyncio.to_thread(os.path.exists, file_path)

    async def write_to_csv_file(
        self,
        file: UploadFile,
        target_filename: Optional[str] = None,
        target_subdir: str = "input",
    ) -> UploadResponse:
        """
        Common method to handle CSV file uploads with proper locking.

        Args:
            file: The CSV file to upload
            target_filename: Optional custom filename (if None, uses original filename)
            target_subdir: Subdirectory within data/ to store the file (default: "input")

        Returns:
            UploadResponse with success status and message

        Raises:
            HTTPException: If file validation fails or upload fails
        """
        # Validate file type
        if not file.filename or not file.filename.endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")

        try:
            # Define the target directory and file path
            target_dir = Path("data") / target_subdir
            filename_to_use = target_filename or file.filename
            if not filename_to_use:
                raise HTTPException(status_code=400, detail="No filename provided")
            target_file = target_dir / filename_to_use

            # Use file-specific write lock to prevent race conditions
            async with self._get_file_rw_lock(str(target_file)).writer:
                # Ensure the target directory exists (run in thread to avoid blocking)
                await asyncio.to_thread(target_dir.mkdir, parents=True, exist_ok=True)

                # Save the uploaded file (run in thread to avoid blocking)
                def _write_file() -> None:
                    with open(target_file, "wb") as buffer:
                        shutil.copyfileobj(file.file, buffer)

                await asyncio.to_thread(_write_file)

            return UploadResponse(
                success=True,
                message=f"CSV file '{file.filename}' uploaded successfully to {target_file}",
                file_path=str(target_file),
            )

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to upload file: {str(e)}"
            )
        finally:
            file.file.close()

    async def delete_file_by_name(
        self,
        filename: str,
        target_subdir: str = "input",
    ) -> FileDeleteResponse:
        """
        Delete a file by name from a specific subdirectory.

        Args:
            filename: Name of the file to delete
            target_subdir: Subdirectory within data/ where the file is located

        Returns:
            FileDeleteResponse with success status and message

        Raises:
            HTTPException: If file doesn't exist or deletion fails
        """
        try:
            # Construct the full file path
            file_path = Path("data") / target_subdir / filename

            # Use file-specific write lock to prevent race conditions
            async with self._get_file_rw_lock(str(file_path)).writer:
                file_exists = await asyncio.to_thread(file_path.exists)
                if not file_exists:
                    raise HTTPException(
                        status_code=404,
                        detail=f"File '{filename}' not found in {target_subdir}",
                    )

                # Delete the file (run in thread to avoid blocking)
                await asyncio.to_thread(file_path.unlink)

            return FileDeleteResponse(
                success=True,
                message=f"File '{filename}' deleted successfully from {target_subdir}",
                file_path=str(file_path),
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file '{filename}': {str(e)}"
            )

    async def delete_file(self, file_path: str) -> FileDeleteResponse:
        """
        Delete a file at the specified path with proper locking.

        Args:
            file_path: Full path to the file to delete

        Returns:
            FileDeleteResponse with success status and message

        Raises:
            HTTPException: If file doesn't exist or deletion fails
        """
        try:
            # Use file-specific write lock to prevent race conditions
            async with self._get_file_rw_lock(file_path).writer:
                file_exists = await asyncio.to_thread(os.path.exists, file_path)
                if not file_exists:
                    raise HTTPException(
                        status_code=404, detail=f"File not found: {file_path}"
                    )

                # Delete the file (run in thread to avoid blocking)
                await asyncio.to_thread(os.remove, file_path)

            return FileDeleteResponse(
                success=True,
                message=f"File deleted successfully: {file_path}",
                file_path=file_path,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete file: {str(e)}"
            )

    async def save_results_to_csv(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        expected_headers: Optional[List[str]] = None,
    ) -> None:
        """
        Save results to a CSV file with proper locking.

        Args:
            results: List of dictionaries containing the results
            output_path: Path where the CSV file should be saved
            expected_headers: Optional list of expected headers for the CSV

        Raises:
            Exception: If saving fails
        """
        try:
            # Use file-specific write lock to prevent race conditions
            async with self._get_file_rw_lock(output_path).writer:
                # Ensure the output directory exists (run in thread to avoid blocking)
                output_dir = Path(output_path).parent
                await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

                if not results:
                    # Create empty CSV with headers if no results
                    if expected_headers:
                        df = pd.DataFrame(columns=expected_headers)
                    else:
                        df = pd.DataFrame()
                else:
                    # Convert results to DataFrame
                    df = pd.DataFrame(results)

                    # Ensure all expected headers are present
                    if expected_headers:
                        for header in expected_headers:
                            if header not in df.columns:
                                df[header] = None

                        # Reorder columns to match expected headers
                        df = df[expected_headers]

                # Save to CSV (run in thread to avoid blocking)
                await asyncio.to_thread(df.to_csv, output_path, index=False)

        except Exception as e:
            logger.error(f"Failed to save results to CSV: {str(e)}")
            raise

    async def append_results_to_csv(
        self,
        results: List[Dict[str, Any]],
        output_path: str,
        expected_headers: Optional[List[str]] = None,
    ) -> None:
        """
        Append results to an existing CSV file or create a new one with proper locking.

        This method supports appending data to existing CSV files while ensuring
        headers are only written once. If the file doesn't exist, it creates
        a new file with headers.

        Args:
            results: List of dictionaries containing the results to append
            output_path: Path where the CSV file should be saved/appended
            expected_headers: Optional list of expected headers for the CSV

        Raises:
            Exception: If appending fails
        """
        try:
            # Use file-specific write lock to prevent race conditions
            async with self._get_file_rw_lock(output_path).writer:
                # Ensure the output directory exists (run in thread to avoid blocking)
                output_dir = Path(output_path).parent
                await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

                if not results:
                    # If no results to append, just return
                    return

                # Convert results to DataFrame
                df = pd.DataFrame(results)

                # Ensure all expected headers are present
                if expected_headers:
                    for header in expected_headers:
                        if header not in df.columns:
                            df[header] = None

                    # Reorder columns to match expected headers
                    df = df[expected_headers]

                # Check if file exists to determine if we need to write headers
                file_exists = await asyncio.to_thread(os.path.exists, output_path)

                if file_exists:
                    # File exists, append without headers (run in thread to avoid blocking)
                    await asyncio.to_thread(
                        df.to_csv, output_path, mode="a", header=False, index=False
                    )
                else:
                    # File doesn't exist, create new file with headers (run in thread to avoid blocking)
                    await asyncio.to_thread(df.to_csv, output_path, index=False)

        except Exception as e:
            logger.error(f"Failed to append results to CSV: {str(e)}")
            raise

    async def read_csv_with_lock(
        self, file_path: str, encoding: str = "utf-8", delimiter: str = ","
    ) -> pd.DataFrame:
        """
        Read a CSV file with proper locking.

        Args:
            file_path: Path to the CSV file
            encoding: File encoding (default: utf-8)
            delimiter: CSV delimiter (default: comma)

        Returns:
            DataFrame containing the CSV data

        Raises:
            Exception: If reading fails
        """
        try:
            # Use file-specific read lock to allow multiple readers
            async with self._get_file_rw_lock(file_path).reader:
                file_exists = await asyncio.to_thread(os.path.exists, file_path)
                if not file_exists:
                    raise FileNotFoundError(f"File not found: {file_path}")

                # Read the CSV file (run in thread to avoid blocking)
                df = await asyncio.to_thread(
                    pd.read_csv, file_path, encoding=encoding, delimiter=delimiter
                )
                return df

        except Exception as e:
            logger.error(f"Failed to read CSV file: {str(e)}")
            raise

    async def load_csv_as_dict_list(
        self, csv_path: str, encoding: str = "utf-8", delimiter: str = ","
    ) -> List[Dict[str, Any]]:
        """
        Generic CSV loader that loads any CSV file and returns a list of dictionaries.
        Each row becomes a dictionary with column names as keys.

        Args:
            csv_path: Path to the CSV file
            encoding: File encoding (default: 'utf-8')
            delimiter: CSV delimiter (default: ',')

        Returns:
            List of dictionaries where each dictionary represents a row with column names as keys

        Raises:
            ValueError: If the CSV file cannot be loaded or is empty
            FileNotFoundError: If the CSV file doesn't exist
        """
        try:
            # Read the CSV file
            df = await self.read_csv_with_lock(
                csv_path, encoding=encoding, delimiter=delimiter
            )
            # Check if the dataframe is empty
            if df.empty:
                raise ValueError(f"CSV file '{csv_path}' is empty")

            # Convert dataframe to list of dictionaries
            # Each row becomes a dictionary with column names as keys
            dict_list = df.to_dict("records")

            # Convert pandas/numpy types to Python native types and ensure string keys
            result_list = []
            for row_dict in dict_list:
                converted_dict: Dict[str, Any] = {}
                for key, value in row_dict.items():
                    # Convert key to string if it isn't already
                    str_key = str(key)
                    # Handle NaN values
                    if pd.isna(value):
                        converted_dict[str_key] = None
                    # Convert numpy types to Python native types
                    elif hasattr(value, "item"):
                        converted_dict[str_key] = value.item()
                    # Ensure strings are properly converted
                    elif isinstance(value, str):
                        converted_dict[str_key] = value.strip()
                    else:
                        converted_dict[str_key] = value
                result_list.append(converted_dict)

            return result_list

        except FileNotFoundError:
            logger.warning(f"CSV file not found: {csv_path}")
            return []
        except pd.errors.EmptyDataError:
            raise ValueError(
                f"CSV file '{csv_path}' is empty or contains no valid data"
            )
        except pd.errors.ParserError as e:
            raise ValueError(f"Error parsing CSV file '{csv_path}': {str(e)}")
        except Exception as e:
            raise ValueError(f"Error loading CSV file '{csv_path}': {str(e)}")
