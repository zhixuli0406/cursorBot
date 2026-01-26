"""
Example Agent Skill for CursorBot

This is a template for creating custom agent skills.
Copy this file and modify it to create your own skills.

Skills placed in the skills/agent/ directory will be automatically loaded.
"""

from src.core.skills import AgentSkill, AgentSkillInfo


class ExampleAgentSkill(AgentSkill):
    """
    Example agent skill that demonstrates the skill structure.
    
    To create your own skill:
    1. Create a new class that inherits from AgentSkill
    2. Implement the `info` property with skill metadata
    3. Implement the `execute` method with your skill logic
    """
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="example_skill",
            description="An example skill that echoes back the input",
            version="1.0.0",
            author="CursorBot",
            enabled=True,  # Set to False to disable
            parameters={
                "message": "The message to echo back",
                "uppercase": "Optional: convert to uppercase (true/false)",
            },
            examples=[
                "Echo 'Hello World'",
                "Say something back to me",
            ],
            categories=["example", "demo"],
        )
    
    async def execute(self, **kwargs) -> dict:
        """
        Execute the skill.
        
        Args:
            **kwargs: Parameters passed to the skill
            
        Returns:
            dict with results or error
        """
        message = kwargs.get("message", "No message provided")
        uppercase = kwargs.get("uppercase", "false").lower() == "true"
        
        if uppercase:
            message = message.upper()
        
        return {
            "status": "success",
            "original_message": kwargs.get("message", ""),
            "processed_message": message,
            "uppercase": uppercase,
        }
    
    async def on_load(self) -> None:
        """Called when skill is loaded."""
        # Initialize any resources here
        pass
    
    async def on_unload(self) -> None:
        """Called when skill is unloaded."""
        # Cleanup resources here
        pass


# You can define multiple skills in one file
class AnotherExampleSkill(AgentSkill):
    """Another example skill."""
    
    @property
    def info(self) -> AgentSkillInfo:
        return AgentSkillInfo(
            name="timestamp",
            description="Get current timestamp",
            parameters={},
            examples=["What time is it?", "Get current timestamp"],
            categories=["utility", "time"],
        )
    
    async def execute(self, **kwargs) -> dict:
        from datetime import datetime
        
        now = datetime.now()
        return {
            "timestamp": now.isoformat(),
            "formatted": now.strftime("%Y-%m-%d %H:%M:%S"),
            "unix": int(now.timestamp()),
        }
