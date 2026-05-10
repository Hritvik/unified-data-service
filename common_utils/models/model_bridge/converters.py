"""
Model Bridge Registry converters.

This module provides utilities for converting between different model types:
- Response Models: API response models
- Native Models: Business logic models with computed fields and methods

Standard conversion pattern:
Response Model <-> Native Model
"""

from typing import Any, Dict, List, Optional

from common_utils.enums import Modality
from common_utils.models.entities import FilterAttribute
from common_utils.models.model_bridge.native import (
    DeploymentInfoNative,
    ModelInfoNative,
    RoutePlanInfoNative,
)
from common_utils.models.model_bridge_registry.responses import (
    DeploymentInfo,
    ModelInfo,
    RoutePlanInfo,
)


def _convert_filter_attributes_to_dict(
    filter_attributes: List[FilterAttribute],
) -> Dict[str, Any]:
    """
    Convert a list of FilterAttribute objects to a dictionary.

    Args:
        filter_attributes: List of FilterAttribute objects

    Returns:
        Dictionary with attribute keys and values
    """
    if not filter_attributes:
        return {}

    result = {}
    for attr in filter_attributes:
        result[attr.key] = attr.value
    return result


def _convert_dict_to_filter_attributes(
    filter_attributes_dict: Dict[str, Any],
) -> List[FilterAttribute]:
    """
    Convert a dictionary to a list of FilterAttribute objects.

    Args:
        filter_attributes_dict: Dictionary with attribute keys and values

    Returns:
        List of FilterAttribute objects
    """
    if not filter_attributes_dict:
        return []

    result = []
    for key, value in filter_attributes_dict.items():
        result.append(FilterAttribute(key=key, value=value))
    return result


def convert_model_info_to_native(model_info: ModelInfo) -> ModelInfoNative:
    """
    Convert a ModelInfo instance to a ModelInfoNative.

    Args:
        model_info: ModelInfo instance

    Returns:
        ModelInfoNative object
    """
    return ModelInfoNative(
        model_name=model_info.model_name,
        filter_attributes=_convert_filter_attributes_to_dict(
            model_info.filter_attributes
        ),
        tags=model_info.tags,
        api_contract=model_info.api_contract,
        input_modality=model_info.input_modality,
        output_modality=model_info.output_modality,
        input_format=model_info.input_format,
        output_format=model_info.output_format,
        is_active=model_info.is_active,
        created_at=model_info.created_at,
        updated_at=model_info.updated_at,
    )


def convert_deployment_info_to_native(
    deployment_info: DeploymentInfo,
    model_info: Optional[ModelInfo] = None,
) -> DeploymentInfoNative:
    """
    Convert a DeploymentInfo instance to a DeploymentInfoNative.

    Args:
        deployment_info: DeploymentInfo instance
        model_info: Optional ModelInfo for API contract lookup

    Returns:
        DeploymentInfoNative object
    """
    deployment_native = DeploymentInfoNative(
        deployment_name=deployment_info.deployment_name,
        filter_attributes=_convert_filter_attributes_to_dict(
            deployment_info.filter_attributes
        ),
        tags=deployment_info.tags,
        model_name=deployment_info.model_name,
        tpm=deployment_info.tpm,
        client_identifier=deployment_info.client_identifier,
        path_identifier=deployment_info.path_identifier,
        is_active=deployment_info.is_active,
        created_at=deployment_info.created_at,
        updated_at=deployment_info.updated_at,
    )

    # Set API contract from model info if available
    if model_info:
        deployment_native.api_contract = model_info.api_contract

    return deployment_native


def convert_route_plan_info_to_native(
    route_plan_info: RoutePlanInfo,
) -> RoutePlanInfoNative:
    """
    Convert a RoutePlanInfo instance to a RoutePlanInfoNative.

    Args:
        route_plan_info: RoutePlanInfo instance

    Returns:
        RoutePlanInfoNative object
    """
    # Convert the route plan configuration from response models to native models
    from common_utils.models.model_bridge.native import (
        RoutePlanConfigurationNative,
        RoutePlanLevelNative,
        RoutePlanRetryConfigNative,
        RoutePlanTimeoutConfigNative,
    )

    # Convert levels
    native_levels = []
    for level in route_plan_info.route_plan.levels:
        # Convert models if available
        native_models = None
        if level.models:
            from common_utils.models.model_bridge.native import RouteLevelModelConfig

            native_models = []
            for model in level.models:
                # Convert model deployments if available
                model_deployments = []
                if hasattr(model, "deployments") and model.deployments:
                    from common_utils.models.model_bridge.native import DeploymentConfig

                    for deployment in model.deployments:
                        model_deployments.append(
                            DeploymentConfig(
                                name=deployment.name,
                                weight=deployment.weight,
                                priority=deployment.priority,
                            )
                        )

                native_models.append(
                    RouteLevelModelConfig(
                        name=model.name,
                        weight=model.weight,
                        priority=model.priority,
                        deployments=model_deployments,
                    )
                )

        # Convert attributes from List[FilterAttribute] to Dict[str, Any] for model_bridge native
        attributes_dict = _convert_filter_attributes_to_dict(level.attributes)

        native_level = RoutePlanLevelNative(
            level=level.level,
            model_selection_strategy=level.model_selection_strategy,
            deployment_selection_strategy=level.deployment_selection_strategy,
            model_attribute_match_strategy=getattr(
                level, "model_attribute_match_strategy", None
            ),
            deployment_attribute_match_strategy=getattr(
                level, "deployment_attribute_match_strategy", None
            ),
            routing_strategy=level.routing_strategy,
            attributes=attributes_dict,
            models=native_models,
        )
        native_levels.append(native_level)

    # Convert retry config
    native_retry_config = RoutePlanRetryConfigNative(
        max_attempts=route_plan_info.route_plan.retry_config.max_attempts,
        max_time_seconds=route_plan_info.route_plan.retry_config.max_time_seconds,
        strict_max_time=route_plan_info.route_plan.retry_config.strict_max_time,
    )

    # Convert timeout config
    native_timeout_config = RoutePlanTimeoutConfigNative(
        timeout_seconds=route_plan_info.route_plan.timeout_config.timeout_seconds,
    )

    # Create the native route plan configuration
    native_route_plan = RoutePlanConfigurationNative(
        levels=native_levels,
        retry_config=native_retry_config,
        timeout_config=native_timeout_config,
    )

    return RoutePlanInfoNative(
        id=route_plan_info.id,
        route_plan_name=route_plan_info.route_plan_name,
        route_plan=native_route_plan,
        is_active=route_plan_info.is_active,
        created_at=route_plan_info.created_at,
        updated_at=route_plan_info.updated_at,
    )


def convert_models_info_to_native(
    models_info: List[ModelInfo],
) -> List[ModelInfoNative]:
    """
    Convert a list of ModelInfo instances to ModelInfoNative objects.

    Args:
        models_info: List of ModelInfo instances

    Returns:
        List of ModelInfoNative objects
    """
    return [convert_model_info_to_native(model_info) for model_info in models_info]


def convert_deployments_info_to_native(
    deployments_info: List[DeploymentInfo],
    models_info: Optional[List[ModelInfo]] = None,
) -> List[DeploymentInfoNative]:
    """
    Convert a list of DeploymentInfo instances to DeploymentInfoNative objects.

    Args:
        deployments_info: List of DeploymentInfo instances
        models_info: Optional list of ModelInfo instances for API contract lookup

    Returns:
        List of DeploymentInfoNative objects
    """
    # Create a lookup map for model info by model name
    model_lookup = {}
    if models_info:
        model_lookup = {model.model_name: model for model in models_info}

    deployment_info_list = []
    for deployment_info in deployments_info:
        # Find corresponding model info for API contract lookup
        model_info = model_lookup.get(deployment_info.model_name)
        deployment_native = convert_deployment_info_to_native(
            deployment_info, model_info
        )
        deployment_info_list.append(deployment_native)

    return deployment_info_list


def convert_route_plans_info_to_native(
    route_plans_info: List[RoutePlanInfo],
) -> List[RoutePlanInfoNative]:
    """
    Convert a list of RoutePlanInfo instances to RoutePlanInfoNative objects.

    Args:
        route_plans_info: List of RoutePlanInfo instances

    Returns:
        List of RoutePlanInfoNative objects
    """
    return [
        convert_route_plan_info_to_native(route_plan_info)
        for route_plan_info in route_plans_info
    ]


def convert_modality_list(modality_values: Any) -> List[Modality]:
    """
    Convert a list of modality values to Modality enum list.

    Args:
        modality_values: List of modality values (strings or enums)

    Returns:
        List of Modality enum values
    """
    if not modality_values:
        return []

    modality_list = []
    for modality_value in modality_values:
        if isinstance(modality_value, Modality):
            modality_list.append(modality_value)
        elif isinstance(modality_value, str):
            try:
                modality_list.append(Modality(modality_value))
            except ValueError:
                # Skip invalid modality values
                continue
        else:
            # Skip invalid modality values
            continue

    return modality_list
