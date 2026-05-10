"""Model bridge registry converter functions.

The legacy ``ModelDocument`` / ``DeploymentDocument`` / ``RoutePlanDocument``
classes were dropped in PR2; only the ``RoutePlan`` document → native →
info chain remains because the model_bridge runtime still consumes registry
data through the ``Native`` shape (and the Beanie docs are duck-type compatible
on the document side).
"""

from common_utils.models.model_bridge_registry.native import (
    DeploymentConfigNative,
    RouteLevelModelConfig,
    RoutePlanConfigurationRegistryNative,
    RoutePlanInfoRegistryNative,
    RoutePlanLevelRegistryNative,
    RoutePlanRetryConfigRegistryNative,
    RoutePlanTimeoutConfigRegistryNative,
)
from common_utils.models.model_bridge_registry.responses import (
    DeploymentConfig,
    RoutePlanConfiguration,
    RoutePlanInfo,
    RoutePlanLevel,
    RoutePlanRetryConfig,
    RoutePlanTimeoutConfig,
)
from common_utils.models.model_bridge_registry.responses import (
    RouteLevelModelConfig as RouteLevelModelConfigResponse,
)


def convert_route_plan_document_to_native(doc) -> RoutePlanInfoRegistryNative:
    """Convert a route-plan document to native form.

    Reads attribute-level fields only — works for both legacy
    ``RoutePlanDocument`` (now retired) and current ``RoutePlanDocument`` since
    they share the nested ``RoutePlanConfigurationDocument`` schema.
    """
    route_plan_config = doc.route_plan

    levels = []
    for level_data in route_plan_config.levels:
        models = None
        if level_data.models:
            models = []
            for model in level_data.models:
                model_deployments = []
                if hasattr(model, "deployments") and model.deployments:
                    for deployment in model.deployments:
                        model_deployments.append(
                            DeploymentConfigNative(
                                name=deployment.name,
                                weight=deployment.weight,
                                priority=deployment.priority,
                            )
                        )

                models.append(
                    RouteLevelModelConfig(
                        name=model.name,
                        weight=model.weight,
                        priority=model.priority,
                        deployments=model_deployments,
                    )
                )

        level = RoutePlanLevelRegistryNative(
            level=level_data.level,
            model_selection_strategy=level_data.model_selection_strategy,
            deployment_selection_strategy=level_data.deployment_selection_strategy,
            model_attribute_match_strategy=level_data.model_attribute_match_strategy,
            deployment_attribute_match_strategy=level_data.deployment_attribute_match_strategy,
            routing_strategy=level_data.routing_strategy,
            attributes=level_data.attributes,
            models=models,
        )
        levels.append(level)

    retry_config = RoutePlanRetryConfigRegistryNative(
        max_attempts=route_plan_config.retry_config.max_attempts,
        max_time_seconds=route_plan_config.retry_config.max_time_seconds,
        strict_max_time=route_plan_config.retry_config.strict_max_time,
    )

    timeout_config = RoutePlanTimeoutConfigRegistryNative(
        timeout_seconds=route_plan_config.timeout_config.timeout_seconds,
    )

    route_plan_config_native = RoutePlanConfigurationRegistryNative(
        levels=levels,
        retry_config=retry_config,
        timeout_config=timeout_config,
    )

    return RoutePlanInfoRegistryNative(
        id=str(doc.id),
        route_plan_name=doc.route_plan_name,
        route_plan=route_plan_config_native,
        is_active=doc.is_active,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def convert_route_plan_native_to_info(
    native: RoutePlanInfoRegistryNative,
) -> RoutePlanInfo:
    """Convert RoutePlanInfoRegistryNative to RoutePlanInfo."""
    levels = []
    for level_data in native.route_plan.levels:
        response_models = None
        if level_data.models:
            response_models = []
            for model in level_data.models:
                model_deployments = []
                if hasattr(model, "deployments") and model.deployments:
                    for deployment in model.deployments:
                        model_deployments.append(
                            DeploymentConfig(
                                name=deployment.name,
                                weight=deployment.weight,
                                priority=deployment.priority,
                            )
                        )

                response_models.append(
                    RouteLevelModelConfigResponse(
                        name=model.name,
                        weight=model.weight,
                        priority=model.priority,
                        deployments=model_deployments,
                    )
                )

        level = RoutePlanLevel(
            level=level_data.level,
            model_selection_strategy=level_data.model_selection_strategy,
            deployment_selection_strategy=level_data.deployment_selection_strategy,
            model_attribute_match_strategy=level_data.model_attribute_match_strategy,
            deployment_attribute_match_strategy=level_data.deployment_attribute_match_strategy,
            routing_strategy=level_data.routing_strategy,
            attributes=level_data.attributes,
            models=response_models,
        )
        levels.append(level)

    retry_config = RoutePlanRetryConfig(
        max_attempts=native.route_plan.retry_config.max_attempts,
        max_time_seconds=native.route_plan.retry_config.max_time_seconds,
        strict_max_time=native.route_plan.retry_config.strict_max_time,
    )

    timeout_config = RoutePlanTimeoutConfig(
        timeout_seconds=native.route_plan.timeout_config.timeout_seconds,
    )

    route_plan_config = RoutePlanConfiguration(
        levels=levels,
        retry_config=retry_config,
        timeout_config=timeout_config,
    )

    return RoutePlanInfo(
        id=native.id,
        route_plan_name=native.route_plan_name,
        route_plan=route_plan_config,
        is_active=native.is_active,
        created_at=native.created_at.isoformat(),
        updated_at=native.updated_at.isoformat(),
    )
