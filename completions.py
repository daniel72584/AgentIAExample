import json
import os

from litellm import completion

from tool import Prompt


def generate_response(prompt: Prompt) -> str:
    """Call LLM to get response"""

    messages = prompt.messages
    tools = prompt.tools

    result = None

    if not tools:
        response = completion(
            api_base="https://models.github.ai/inference",
            model="openai/gpt-4o",
            messages=messages,
            max_tokens=1024,
            api_key=os.getenv('OPEN_IA_KEY')
        )
        result = response.choices[0].message.content
    else:
        response = completion(
            api_base="https://models.github.ai/inference",
            model="openai/gpt-4o",
            messages=messages,
            tools=tools,
            max_tokens=1024,
            api_key=os.getenv('OPEN_IA_KEY')
        )

        if response.choices[0].message.tool_calls:
            tool = response.choices[0].message.tool_calls[0]
            result = {
                "tool": tool.function.name,
                "args": json.loads(tool.function.arguments),
            }
            result = json.dumps(result)
        else:
            result = response.choices[0].message.content


    return result