"""
Tool Registry System
Provides a unified interface for LLM to discover and use tools.
"""

import json
import logging
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from abc import ABC, abstractmethod


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolResult:
    """Result from tool execution"""
    success: bool
    data: Any = None
    error: str = None


class BaseTool(ABC):
    """Base class for all tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> List[ToolParameter]:
        """Tool parameters"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary for LLM"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    param.name: {
                        "type": param.type,
                        "description": param.description
                    } for param in self.parameters
                },
                "required": [param.name for param in self.parameters if param.required]
            }
        }


class ToolRegistry:
    """Registry to manage all available tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self.logger = logging.getLogger(__name__)
    
    def register(self, tool: BaseTool):
        """Register a tool"""
        self.tools[tool.name] = tool
        self.logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions for LLM"""
        return [tool.to_dict() for tool in self.tools.values()]
    
    async def execute_tool(self, name: str, parameters: Dict[str, Any]) -> ToolResult:
        """Execute a tool with parameters"""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        try:
            self.logger.info(f"Executing tool: {name} with parameters: {parameters}")
            result = await tool.execute(**parameters)
            self.logger.info(f"Tool {name} executed successfully: {result.success}")
            return result
        except Exception as e:
            error_msg = f"Error executing tool {name}: {str(e)}"
            self.logger.error(error_msg)
            return ToolResult(
                success=False,
                error=error_msg
            )
    
    def get_available_tools_description(self) -> str:
        """Get a description of all available tools for LLM context"""
        descriptions = []
        for tool in self.tools.values():
            params_desc = ", ".join([f"{p.name}({p.type})" for p in tool.parameters])
            descriptions.append(f"- {tool.name}({params_desc}): {tool.description}")
        
        return "Available tools:\n" + "\n".join(descriptions)


# Global registry instance
tool_registry = ToolRegistry()