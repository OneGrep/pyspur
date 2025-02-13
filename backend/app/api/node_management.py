from typing import Annotated, Any, Dict, List
from fastapi import APIRouter, Depends
from ..nodes.factory import NodeFactory, get_node_factory
from ..nodes.llm._utils import LLMModels
from ..schemas.node_type_schemas import NodeTypeSchema
from ..nodes.node_types import NodeGroup

from loguru import logger

router = APIRouter()


@router.get(
    "/supported_types/", description="Get the schemas for all available node types"
)
async def get_node_types(
    node_factory: Annotated[NodeFactory, Depends(get_node_factory)]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Returns the schemas for all available node types.
    """
    # get the schemas for each node class
    node_groups: Dict[NodeGroup, List[NodeTypeSchema]] = (
        node_factory.get_all_node_types_by_group()
    )

    response: Dict[str, List[Dict[str, Any]]] = {}
    for node_group, node_types in node_groups.items():
        logger.debug(f"processingnode_group {node_group} with {len(node_types)} node types")
        group_node_data: List[Dict[str, Any]] = []
        for node_type in node_types:
            node_data = node_data_from_schema(node_type)
            group_node_data.append(node_data)
        response[node_group.name] = group_node_data

    return response


def node_data_from_schema(node_type: NodeTypeSchema) -> Dict[str, Any]:
    node_class = node_type.node_class
    try:
        input_schema = node_class.input_model.model_json_schema()
    except AttributeError:
        input_schema = {}
    try:
        output_schema = node_class.output_model.model_json_schema()
    except AttributeError:
        output_schema = {}

        # Get the config schema and update its title with the display name
    config_schema = node_class.config_model.model_json_schema()
    config_schema["title"] = node_type.display_name
    has_fixed_output = node_class.config_model.model_fields["has_fixed_output"].default

    node_schema: Dict[str, Any] = {
        "name": node_type.node_type_name,
        "input": input_schema,
        "output": output_schema,
        "config": config_schema,
        "visual_tag": node_class.get_default_visual_tag().model_dump(),
        "has_fixed_output": has_fixed_output,
    }

    # Add model constraints if this is an LLM node
    if node_type.node_type_name in ["LLMNode", "SingleLLMCallNode"]:
        model_constraints = {}
        for model_enum in LLMModels:
            model_info = LLMModels.get_model_info(model_enum.value)
            if model_info:
                model_constraints[model_enum.value] = (
                    model_info.constraints.model_dump()
                )
        node_schema["model_constraints"] = model_constraints

    # Add the logo if available
    logo = node_type.logo
    if logo:
        node_schema["logo"] = logo

    category = node_type.category
    if category:
        node_schema["category"] = category
    return node_schema
