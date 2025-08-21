import os
from typing import List

from dotenv import load_dotenv

from actions import PythonActionRegistry
from agent import Agent
from completions import generate_response
from environment import Environment
from goal import Goal, AgentFunctionCallingActionLanguage
from tool_data import register_tool, Prompt

load_dotenv()
print(os.getenv('OPEN_IA_KEY'))

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    @register_tool()
    def create_and_consult_expert(action_context: ActionContext,
                                  expertise_domain: str,
                                  problem_description: str) -> str:
        """
        Dynamically create and consult an expert persona based on the specific domain and problem.

        Args:
            expertise_domain: The specific domain of expertise needed
            problem_description: Detailed description of the problem to be solved

        Returns:
            The expert's insights and recommendations
        """
        # Step 1: Dynamically generate a persona description
        persona_description_prompt = f"""
        Create a detailed description of an expert in {expertise_domain} who would be 
        ideally suited to address the following problem:

        {problem_description}

        Your description should include:
        - The expert's background and experience
        - Their specific areas of specialization within {expertise_domain}
        - Their approach to problem-solving
        - The unique perspective they bring to this type of challenge
        """

        generate_response = action_context.get("llm")
        persona_description = generate_response(Prompt(messages=[
            {"role": "user", "content": persona_description_prompt}
        ]))

        # Step 2: Generate a specialized consultation prompt
        consultation_prompt_generator = f"""
        Create a detailed consultation prompt for an expert in {expertise_domain} 
        addressing the following problem:

        {problem_description}

        The prompt should guide the expert to provide comprehensive insights and
        actionable recommendations specific to this problem.
        """

        consultation_prompt = generate_response(Prompt(messages=[
            {"role": "user", "content": consultation_prompt_generator}
        ]))

        # Step 3: Consult the dynamically created persona
        return prompt_expert(
            action_context=action_context,
            description_of_expert=persona_description,
            prompt=consultation_prompt
        )
    # First, we'll define our tools using decorators
    @register_tool()
    def prompt_expert(action_context: ActionContext, description_of_expert: str, prompt: str) -> str:
        """
        Generate a response from an expert persona.

        The expert's background and specialization should be thoroughly described to ensure
        responses align with their expertise. The prompt should be focused on topics within
        their domain of knowledge.

        Args:
            description_of_expert: Detailed description of the expert's background and expertise
            prompt: The specific question or task for the expert

        Returns:
            The expert's response
        """
        generate_response = action_context.get("llm")
        response = generate_response(Prompt(messages=[
            {"role": "system",
             "content": f"Act as the following expert and respond accordingly: {description_of_expert}"},
            {"role": "user", "content": prompt}
        ]))
        return response

    @register_tool(tags=["file_operations", "write"])
    def write_file(
            name: str,
            content: str,
            overwrite: bool = True,
            append: bool = False,
            create_parents: bool = True,
            encoding: str = "utf-8",
    ) -> str:
        """
        Writes text content to a file.

        Args:
            name: Target file path, e.g. "README.md"
            content: Text to write
            overwrite: If True, overwrite existing file (ignored if append is True)
            append: If True, append to the file instead of overwriting
            create_parents: Create parent directories if missing
            encoding: File encoding to use

        Returns:
            A short status message describing what happened
        """
        # Resolve mode
        if append:
            mode = "a"
        else:
            if not overwrite and os.path.exists(name):
                raise FileExistsError(f"Refusing to overwrite existing file: {name}")
            mode = "w"

        # Make sure parent dirs exist if requested
        parent = os.path.dirname(name)
        if parent and create_parents:
            os.makedirs(parent, exist_ok=True)

        # Write the thing
        with open(name, mode, encoding=encoding) as f:
            written = f.write(content)

        action = "appended" if append else ("overwrote" if overwrite else "created")
        return f"{action} {written} bytes to {os.path.abspath(name)}"

    @register_tool(tags=["file_operations", "read"])
    def read_project_file(name: str) -> str:
        """Reads and returns the content of a specified project file.

        Opens the file in read mode and returns its entire contents as a string.
        Raises FileNotFoundError if the file doesn't exist.

        Args:
            name: The name of the file to read

        Returns:
            The contents of the file as a string
        """
        with open(name, "r") as f:
            return f.read()


    @register_tool(tags=["file_operations", "list"])
    def list_project_files() -> List[str]:
        """Lists all Python files in the current project directory.

        Scans the current directory and returns a sorted list of all files
        that end with '.py'.

        Returns:
            A sorted list of Python filenames
        """
        return sorted([file for file in os.listdir(".")
                       if file.endswith(".py")])


    @register_tool(tags=["system"], terminal=True)
    def terminate(message: str) -> str:
        """Terminates the agent's execution with a final message.

        Args:
            message: The final message to return before terminating

        Returns:
            The message with a termination note appended
        """
        return f"{message}\nTerminating..."


    # Define the agent's goals
    goals = [
         Goal(
            priority=1,
            name="Write README",
            description=(
                "Draft a complete README for the project. "
                "When ready, persist it to disk by calling write with "
                "name='README2.md' and the README content. "
                "After successfully writing, verify by calling read_project_file('README2.md'). "
                "Only then call terminate and include a short success note."
            ),
        ),
        Goal(priority=1,
             name="Terminate",
             description="Call terminate when done and provide a complete README for the project in the message parameter")
    ]

    # Create an agent instance with tag-filtered actions
    agent = Agent(
        goals=goals,
        agent_language=AgentFunctionCallingActionLanguage(),
        # The ActionRegistry now automatically loads tools with these tags
        action_registry=PythonActionRegistry(tags=["file_operations","list","read","write", "system"]),
        generate_response=generate_response,
        environment=Environment()
    )

    # Run the agent with user input
    user_input = "Write a README for this project."
    final_memory = agent.run(user_input)
    print(final_memory.get_memories())