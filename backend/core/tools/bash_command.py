import subprocess
from typing import Optional
from dataclasses import dataclass

from agents import function_tool


@dataclass
class BashCommandOutput:
    """Output from a bash command execution.
    
    Attributes:
        stdout: The standard output from the command
        stderr: The standard error output from the command
        return_code: The command's exit code
        success: Boolean indicating if the command executed successfully
    """
    stdout: str
    stderr: str
    return_code: int
    success: bool


class BashCommandTool:
    """A tool for executing bash commands with safety measures."""
    
    def __init__(self, allowed_commands: Optional[list[str]] = None):
        """Initialize the BashCommandTool.
        
        Args:
            allowed_commands: List of allowed command prefixes. If None, all commands are allowed
                            (use with caution!)
        """
        self.allowed_commands = allowed_commands or []

    def _is_command_allowed(self, command: str) -> bool:
        """Check if the command is in the allowed list.
        
        Args:
            command: The command to check
            
        Returns:
            bool: True if command is allowed, False otherwise
        """
        if not self.allowed_commands:
            return True
            
        return any(command.startswith(allowed) for allowed in self.allowed_commands)
    
    async def execute(self, command: str, timeout: int = 30) -> BashCommandOutput:
        """Execute a bash command asynchronously.
        
        Args:
            command: The command to execute
            timeout: Maximum execution time in seconds
            
        Returns:
            BashCommandOutput: Object containing command execution results
            
        Raises:
            ValueError: If command is not in allowed list
            subprocess.TimeoutExpired: If command execution exceeds timeout
            subprocess.SubprocessError: If command execution fails
        """
        if not self._is_command_allowed(command):
            raise ValueError(f"Command '{command}' is not in the allowed list")
            
        try:
            # Execute command with timeout
            process = subprocess.run(
                command,
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout
            )
            
            return BashCommandOutput(
                stdout=process.stdout,
                stderr=process.stderr,
                return_code=process.returncode,
                success=process.returncode == 0
            )
            
        except subprocess.TimeoutExpired as e:
            return BashCommandOutput(
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                return_code=-1,
                success=False
            )
            
        except subprocess.SubprocessError as e:
            return BashCommandOutput(
                stdout="",
                stderr=str(e),
                return_code=-1,
                success=False
            )



@function_tool
def bash_command(command: str) -> BashCommandOutput:
    """Execute a bash command."""
    return BashCommandTool().execute(command)


if __name__ == "__main__":
    import asyncio
    # Create tool with allowed commands
    bash_tool = BashCommandTool(allowed_commands=['ls', 'pwd', 'echo'])

    # Execute command
    result = asyncio.run(bash_tool.execute('ls -la'))
    if result.success:
        print(f"Output: {result.stdout}")
    else:
        print(f"Error: {result.stderr}")
