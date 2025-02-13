from fastapi import Depends
from onegrep.mcp.resource import ToolResource
from onegrep.mcp.toolcall import CallToolResult
from onegrep.sdk.toolbox import Toolbox

from typing import Annotated, List, Dict, Any
from .node_types import NodeGroup, NodeTypeSchema
from .base import BaseNode, BaseNodeConfig, BaseNodeInput, BaseNodeOutput
from .repository import NodeRepository
from ..schemas.node_type_schemas import NodeTypeClassGenerator

from pydantic import BaseModel

from loguru import logger

class OneGrepNode(BaseNode):

    _tool_resource: ToolResource

    # ! TODO: This is not generic enough. We need to be able to handle different input and output types.
    async def run(self, input: BaseModel) -> BaseModel:
        logger.info(f"running tool '{self._tool_resource.tool_schema.name}' with input: {input}")
        args = input.model_dump().get("input_node", {}) # ! How to know what the input node key is?
        logger.info(f"MCP ToolCall with args: {args}")
        result: CallToolResult = await self._tool_resource.atool_call(**args)()
        if result.isError:
            raise Exception(f"Error calling tool: {result}")
        
        # ! TODO: Handle different content types
        text_content = result.content[0]
        if text_content.type == "text":
            # We assumpe the text content is a JSON string that we can parse into the output model
            return self.output_model.model_validate_json(text_content.text)
        else:
            raise Exception(f"Unexpected content type: {text_content.type}")


class OneGrepNodeConfig(BaseNodeConfig):
    has_fixed_output: bool = False


class OneGrepNodeInput(BaseNodeInput):
    pass


class OneGrepNodeOutput(BaseNodeOutput):
    pass


async def async_get_toolbox():
    return await Toolbox.create_async(logger=logger)


def dynamic_onegrep_node_type_name(r: ToolResource) -> str:
    return "".join(part.capitalize() for part in r.tool_name.split("_"))


def dynamic_onegrep_config_model_generator(r: ToolResource) -> BaseModel:
    return type(
        dynamic_onegrep_node_type_name(r) + "NodeConfig", (OneGrepNodeConfig,), {}
    )

def dynamic_onegrep_input_model_generator(r: ToolResource) -> BaseModel:
    return type(
        dynamic_onegrep_node_type_name(r) + "NodeInput", (OneGrepNodeInput,), {}
    )


def dynamic_onegrep_output_model_generator(r: ToolResource) -> BaseModel:
    return type(
        dynamic_onegrep_node_type_name(r) + "NodeOutput", (OneGrepNodeOutput,), {}
    )


def dynamic_onegrep_node_class_generator(r: ToolResource) -> BaseNode:
    tool_name_parts = r.tool_name.split("_")
    # Convention: CamelCase for actual class name, snake_case for the "name" of the node
    node_class_type_name = (
        "".join(part.capitalize() for part in tool_name_parts) + "Node"
    )
    node_class_name = "_".join(part.lower() for part in tool_name_parts) + "_node"
    node_class = type(node_class_type_name, (OneGrepNode,), {})
    node_class.name = node_class_name
    node_class.display_name = r.tool_schema.name
    # node_class.logo = "/images/onegrep.png" # ! TODO: Support logos
    # node_class.category = "OneGrep" # ! TODO: If use similar pattern for "Integrations", this is the sub-category?

    node_class.config_model = dynamic_onegrep_config_model_generator(r)
    node_class.input_model = dynamic_onegrep_input_model_generator(r)
    node_class.output_model = dynamic_onegrep_output_model_generator(r)

    # Set the tool resource on the node class (so we can access it in the run method)
    node_class._tool_resource = r
    return node_class


def node_group_from_tool_resource(r: ToolResource) -> NodeGroup:
    # Onegrep server names are generally hyphenated (but not guaranteed)
    server_name_parts = r.remote_client_config.name.split("-")
    group_name = "".join(part.capitalize() for part in server_name_parts)
    return NodeGroup(name=group_name)


class OneGrepNodeClassGenerator(NodeTypeClassGenerator):
    def __init__(self, tool_resource: ToolResource):
        self._tool_resource = tool_resource

    def __call__(self) -> BaseNode:
        return dynamic_onegrep_node_class_generator(self._tool_resource)


def get_onegrep_node_type_schemas_by_group(
    toolbox: Toolbox,
) -> Dict[NodeGroup, List[NodeTypeSchema]]:
    """
    Returns a dictionary of all available OneGrep node types.
    """
    resources: List[ToolResource] = toolbox.get_all_resources()
    schemas_by_group: Dict[NodeGroup, List[NodeTypeSchema]] = {}
    for r in resources:
        node_class_generator: NodeTypeClassGenerator = OneGrepNodeClassGenerator(r)

        node_class = node_class_generator()
        input_schema = node_class.input_model.model_json_schema()
        output_schema = node_class.output_model.model_json_schema()
        config_schema = node_class.config_model.model_json_schema()

        # Important to set so the UI displays the correct title and description
        config_schema["title"] = r.tool_schema.name
        config_schema["description"] = r.tool_schema.description

        visual_tag = node_class.get_default_visual_tag()

        node_schema_dict: Dict[str, Any] = {
            "node_type_name": node_class.name,
            "class_name": node_class.name,
            "input": input_schema,
            "output": output_schema,
            "config": config_schema,
            "visual_tag": visual_tag.model_dump(),
            "node_class_generator": node_class_generator,
        }
        node_schema = NodeTypeSchema.model_validate(node_schema_dict)

        node_group = node_group_from_tool_resource(r)
        if node_group not in schemas_by_group:
            schemas_by_group[node_group] = []
        schemas_by_group[node_group].append(node_schema)

    return schemas_by_group


class OneGrepNodeRepository(NodeRepository):
    """
    OneGrep node repository that uses a database to store node types.
    """

    def __init__(self, toolbox: Toolbox):
        super().__init__()
        self.toolbox = toolbox
        self._cached_node_schemas: Dict[NodeGroup, List[NodeTypeSchema]] = {}

    def _cache_node_schemas(self) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        if self._cached_node_schemas:
            return self._cached_node_schemas
        self._cached_node_schemas = get_onegrep_node_type_schemas_by_group(self.toolbox)
        return self._cached_node_schemas

    def get_node_groups(self) -> List[NodeGroup]:
        return self._cache_node_schemas().keys()

    def get_node_types_for_group(self, group: NodeGroup) -> List[NodeTypeSchema]:
        return self._cache_node_schemas().get(group, [])

    def get_all_node_types_by_group(self) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        return self._cache_node_schemas()
    
    def get_node_type(self, node_type_name: str) -> NodeTypeSchema:
        for group in self.get_node_groups():
            for node_type in self.get_node_types_for_group(group):
                if node_type.node_type_name == node_type_name:
                    return node_type
        raise ValueError(f"Node type '{node_type_name}' not found.")

    def is_valid_node_type(self, raw_node_type_name: str) -> bool:
        # TODO: Validate
        return True


async def get_onegrep_node_repository(
    toolbox: Annotated[Toolbox, Depends(async_get_toolbox)]
) -> OneGrepNodeRepository:
    return OneGrepNodeRepository(toolbox)
