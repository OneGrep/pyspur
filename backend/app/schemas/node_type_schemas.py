import importlib
from typing import Callable, Optional

from pydantic import BaseModel

from ..nodes.base import BaseNode

def import_node_class(module: str, class_name: str) -> BaseNode:
    module = importlib.import_module(name=f"{module}", package="app")
    return getattr(module, class_name)

NodeTypeClassGenerator = Callable[[], BaseNode]

class NodeTypeSchema(BaseModel):
    node_type_name: str
    class_name: str
    module: Optional[str] = None # Only needed if the node is statically defined

    node_class_generator: Optional[NodeTypeClassGenerator] = None

    @property
    def node_class(self):
        if self.node_class_generator:
            return self.node_class_generator()
        if self.module:
            return import_node_class(self.module, self.class_name)
        raise ValueError("Node class not found")

    @property
    def input_model(self):
        return self.node_class.input_model

    @property
    def display_name(self) -> str:
        """Get the display name for the node type, falling back to class name if not set."""
        node_class = self.node_class
        return node_class.display_name or node_class.__name__
    
    @property
    def logo(self) -> str:
        """Get the logo for the node type, falling back to None if not set."""
        node_class = self.node_class
        return node_class.logo or ""
    
    @property
    def category(self) -> str:
        """Get the category for the node type, falling back to None if not set."""
        node_class = self.node_class
        return node_class.category or ""

    @property
    def config_title(self) -> str:
        """Get the title to use for the config, using display name."""
        return self.display_name


class MinimumNodeConfigSchema(BaseModel):
    node_type: NodeTypeSchema
