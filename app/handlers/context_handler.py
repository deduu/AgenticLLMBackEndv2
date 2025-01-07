from collections.abc import Iterable

class ContextPreparer:
    def __init__(self):
        self.handlers = {
            'RAG': self.prepare_rag_context,
            'Action': self.prepare_function_call_context,
            'Reasoning': self.prepare_reasoning_context
            # Add other types here if needed
        }

    def prepare_context(self, context):
        context_str = ""
        if isinstance(context, dict):  # Check if context is a dictionary
            for subquery, details in context.items():
                if not isinstance(details, dict) or 'Type' not in details:
                    continue  # Skip if details are not a dictionary or 'Type' is missing
                handler = self.handlers.get(details['Type'])
                if handler:
                    context_str += handler(details)
                else:
                    context_str += f"\n- Unknown Type: {details.get('Type', 'None')}\n"
        return context_str

    def prepare_rag_context(self, details):
        context_str = ""
        sources = details.get('Source', [])
        if not isinstance(sources, list):  # Ensure 'Source' is a list
            sources = []

        for source in sources:
            name = source.get('name', 'Unnamed Source')
            text = source.get('text', 'None')
            url = source.get('url', '#')
            page = source.get('page', '#')
            # context_str += f"\n- Document: [{name}]({url})\n  Text: {text}\n"
            context_str += f"\n- name: {name}\n  page: {page}\n  url: {url}\n  text: {text}\n"
        return context_str

    def prepare_function_call_context(self, details):
        context_str = ""
        sources = details.get('Source', [])
        if not isinstance(sources, list):  # Ensure 'Source' is treated as a list
            sources = []

        for source in sources:
            function_calls = source.get('FunctionName', [])
            if not isinstance(function_calls, list):  # Ensure function calls are a list
                function_calls = []

            output = source.get('Output', 'No Output')

            for function_call in function_calls:
                function_name = function_call.get('name', 'Unknown Function')
                arguments = function_call.get('arguments', {})
                if not isinstance(arguments, dict):  # Ensure arguments are a dictionary
                    arguments = {}
                context_str += f"\n- Function: [{function_name}]\n"
                context_str += f"  Arguments: {arguments}\n"
                context_str += f"  Output: {output}\n"

        return context_str

    def prepare_reasoning_context(self, details):
        context_str = ""
        sources = details.get('Source', [])
        if not isinstance(sources, list):  # Ensure 'Source' is a list
            sources = []

        for source in sources:
            name = source.get('name', 'Unnamed Source')
            text = source.get('text', 'None')
            url = source.get('url', '#')
            context_str += f"\n- Non-document: [{name}]({url})\n  Text: {text}\n"
        return context_str
