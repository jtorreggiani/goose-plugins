from exchange import Exchange, Message, Text
from exchange.content import Content
from exchange.providers import AnthropicProvider
from goose.toolkit.base import Toolkit, tool
from goose.utils.ask import ask_an_ai
from goose_plugins.utils.selenium_web_browser import get_web_page_content
from goose_plugins.utils.serper_search import serper_search
import queue
import time
import threading
import os


class CriticalSystemsThinking(Toolkit):
    """Critical systems thinking toolkit for understanding and solving complex problems."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_queue = queue.Queue()
        self.autonomous_mode = False
        self.ongoing_tasks = {}
        self.completed_tasks = []

    def message_content(self, content: Content) -> Text:
        if isinstance(content, Text):
            return content
        else:
            return Text(str(content))

    def notify(self, message: str):
        """Standardized notification method for concise status updates."""
        self.notifier.status(f"[CST] {message[:50]}...")

    def add_task(self, task_id, task_description, duration):
        """Add a task to the ongoing tasks dictionary."""
        self.ongoing_tasks[task_id] = {
            "description": task_description,
            "start_time": time.time(),
            "duration": duration
        }

    def complete_task(self, task_id, result):
        """Move a task from ongoing to completed and post a message in the chat."""
        if task_id in self.ongoing_tasks:
            task = self.ongoing_tasks.pop(task_id)
            task["result"] = result
            task["end_time"] = time.time()
            self.completed_tasks.append(task)
            # self.post_to_chat(task_id, f"Task '{task['description']}' has completed. Result: {result}")

    # def post_to_chat(self, task_id, message):
    #     """Post a message to the chat."""
    #     self.notifier.status(f"[Task {task_id}] {message}")
    #     print(f"[Task {task_id}] {message}")
    #     self.notifier.status(f"[Task {task_id}] {message}")


    def notify_user(self, message):
        """Notify the user when help is needed."""
        # Implement the notification method here (e.g., send an email, push notification, etc.)
        print(f"[User Notification] {message}")

    @tool
    def autonomous_loop(self, task_description: str, duration: str = "10s"):
        """
        Run a task autonomously in the background and trigger an Apple dialog box after the specified duration.

        Args:
            task_description (str): A description of the task to be simulated.
            duration (str): The duration of the task. Format: "<number><unit>".
                            Units: 's' for seconds, 'm' for minutes, 'h' for hours.
                            Examples: "30s", "5m", "1h". Default: "10s".

        Returns:
            str: A message indicating the task has been started.
        """
        # Convert duration string to seconds
        duration_value = int(duration[:-1])
        duration_unit = duration[-1].lower()
        if duration_unit == 's':
            duration_seconds = duration_value
        elif duration_unit == 'm':
            duration_seconds = duration_value * 60
        elif duration_unit == 'h':
            duration_seconds = duration_value * 3600
        else:
            raise ValueError("Invalid duration format. Use 's' for seconds, 'm' for minutes, or 'h' for hours.")
        task_id = f"task_{int(time.time())}"

        def background_task():
            time.sleep(duration_seconds)

            provider = AnthropicProvider.from_env()

            exchange = Exchange(provider=provider, model="claude-3-5-sonnet-20240620", messages=[], system=None)
            request_input = f"""
            Simulate a response to task_description: {task_description}
            """
            response = ask_an_ai(input=request_input, exchange=exchange, no_history=False)
            response_text = response.content[0].text
            # Trigger the Apple dialog using osascript
            dialog_command = f'display dialog "Task completed" buttons {{"OK"}} default button "OK" with title "Task Completed"'
            os.system(f"osascript -e '{dialog_command}'")
            self.complete_task(task_id, f"Task '{task_description}' completed.")

        self.autonomous_mode = True
        self.notify(f"Starting background task: {task_description}")
        self.add_task(task_id, task_description, duration_seconds)
        
        # Start the background task in a separate thread
        thread = threading.Thread(target=background_task)
        thread.start()

        return f"Background task '{task_description}' (ID: {task_id}) has been started with a duration of {duration}. You can continue interacting while it's running."

    @tool
    def get_background_job_status(self):
        """
        Get the status of all background jobs (ongoing and completed).

        Returns:
            str: A formatted string containing the status of all background jobs.
        """
        current_time = time.time()
        status = "Background Job Status:\n\n"

        status += "Ongoing Tasks:\n"
        for task_id, task in self.ongoing_tasks.items():
            elapsed_time = current_time - task["start_time"]
            remaining_time = max(0, task["duration"] - elapsed_time)
            status += f"- Task ID: {task_id}\n"
            status += f"  Description: {task['description']}\n"
            status += f"  Elapsed Time: {elapsed_time:.2f} seconds\n"
            status += f"  Remaining Time: {remaining_time:.2f} seconds\n\n"

        status += "Completed Tasks:\n"
        for task in self.completed_tasks:
            status += f"- Task ID: {task['description']}\n"
            status += f"  Description: {task['description']}\n"
            status += f"  Duration: {task['end_time'] - task['start_time']:.2f} seconds\n"
            status += f"  Result: {task['result']}\n\n"

        return status

    def check_task_status(self):
        """Check if any tasks have completed and return their results."""
        return [task["result"] for task in self.completed_tasks]

    @tool
    def structured_analysis(self, problem: str) -> str:
        """
        Perform a structured analysis of the given problem using the MECE principle.

        Args:
            problem (str): A description of the problem to analyze.

        Returns:
            response (str): A JSON string containing the structured analysis.
        """
        self.notify("Performing structured analysis")

        provider = AnthropicProvider.from_env()
        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=[],
            system=None
        )

        request_input = f"""
        Perform a structured analysis of the following problem using the MECE (Mutually Exclusive, Collectively Exhaustive) principle:
        {problem}

        Return the results as a JSON string with the following structure:
        {{
            "problem": "Brief restatement of the problem",
            "categories": [
                {{
                    "name": "Category Name",
                    "elements": ["Element 1", "Element 2", ...],
                    "analysis": "Brief analysis of this category"
                }},
                ...
            ],
            "conclusion": "Overall conclusion based on the structured analysis"
        }}
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    @tool
    def search(self, query: str) -> str:
        """
        Search the web for information using the Serper API. This will return a list of search results.

        Args:
            query (str): query to search for.

        Returns:
            response (str): A JSON response containing search results.
        """
        self.notifier.status("searching...")

        return serper_search(query)

    @tool
    def analyze_request(self, statement: str) -> str:
        """
        When a request is unclear, high-level or ambiguous use this tool to
        analyze the response and provide a well thought out response. You should
        return a well thought out response to the statement or question.

        Args:
            statement (str): description of problem or errors seen.

        Returns:
            response (str): A well thought out response to the statement or question.
        """

        self.notifier.status("analyzing request...")

        provider = AnthropicProvider.from_env()

        existing_messages_copy = [
            Message(role=msg.role, content=[self.message_content(content) for content in msg.content])
            for msg in self.exchange_view.processor.messages
        ]

        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=existing_messages_copy,
            system=self.system_prompt(),
        )

        request_input = f"""
          Analyze the user statement: {statement}
          If you need to immediately clarify something and it's something
          short and simple, respond with your question(s).
          If you need multiple questions, you can ask multiple questions.
          Please bullet point your questions.
          Limit your response to 5 questions.
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=False)
        return response.content[0].text

    @tool
    def review_web_page(self, url: str) -> str:
        """
        Review the content of a web page by providing a summary of the content.

        Args:
            url (str): URL of the web page to review.

        Returns:
            response (str): A summary of the content of the web page.
        """

        self.notifier.status(f"fetching content from {url}")

        # Get the text content of the web page
        web_content = ""
        try:
            web_content = get_web_page_content(url)
        except Exception as e:
            return f"Error: {str(e)}"

        self.notifier.status(f"reviewing content: {web_content[:50]}...")

        provider = AnthropicProvider.from_env()

        exchange = Exchange(provider=provider, model="claude-3-5-sonnet-20240620", messages=[], system=None)
        request_input = f"""
          summarize the following content: {web_content}
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=False)
        return response.content[0].text

    @tool
    def consider_solutions(self, statement: str) -> str:
        """
        Provide a well thought out response to the statement summarize the
        problem and provide a solution or a set of solutions.

        Args:
            statement (str): description of problem or errors seen.

        Returns:
            response (str): A well thought out response to the statement or question.
        """

        self.notifier.status("considering solutions...")

        provider = AnthropicProvider.from_env()

        existing_messages_copy = [
            Message(role=msg.role, content=[self.message_content(content) for content in msg.content])
            for msg in self.exchange_view.processor.messages
        ]

        exchange = Exchange(
            provider=provider, model="claude-3-5-sonnet-20240620", messages=existing_messages_copy, system=None
        )

        request_input = f"""
          Analyze the user statement: {statement}
          Consider the existing message history and provide a well thought out response.
          Provide one or more potential solutions to the problem.
          Limit your response to 5 solutions.
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=False)
        return response.content[0].text

    @tool
    def stakeholder_analysis(self, problem_statement: str) -> str:
        """
        Identify and analyze key stakeholders related to the given problem.

        Args:
            problem_statement (str): A description of the problem or situation.

        Returns:
            response (str): A JSON string containing a list of stakeholders, their interests, and potential impacts.
        """
        self.notifier.status("Analyzing stakeholders...")

        provider = AnthropicProvider.from_env()

        existing_messages_copy = [
            Message(role=msg.role, content=[self.message_content(content) for content in msg.content])
            for msg in self.exchange_view.processor.messages
        ]

        exchange = Exchange(
            provider=provider, model="claude-3-5-sonnet-20240620", messages=existing_messages_copy, system=None
        )

        request_input = f"""
        Analyze the following problem statement and identify key stakeholders:
        {problem_statement}
        For each stakeholder, determine their interests and potential impacts.
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    @tool
    def generate_future_scenarios(self, problem_statement: str, time_horizon: str) -> str:
        """
        Generate potential future scenarios based on the given problem statement and time horizon.

        Args:
            problem_statement (str): A description of the current problem or situation.
            time_horizon (str): The future time frame to consider (e.g., "5 years", "10 years", "50 years").

        Returns:
            response (str): A JSON string containing a list of potential future scenarios.
        """
        self.notifier.status("Generating future scenarios...")

        provider = AnthropicProvider.from_env()
        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=[],
            system=None
        )

        request_input = f"""
        Based on the following problem statement and time horizon, generate potential future scenarios:
        Problem: {problem_statement}
        Time Horizon: {time_horizon}

        Consider various factors such as technological advancements, societal changes, environmental impacts, and potential policy shifts.

        Return the results as a JSON string with the following structure:
        {{
            "scenarios": [
                {{
                    "name": "Scenario Name",
                    "description": "Brief description of the scenario",
                    "key_factors": ["Factor 1", "Factor 2", ...],
                    "potential_outcomes": ["Outcome 1", "Outcome 2", ...]
                }},
                ...
            ]
        }}

        Generate at least 3 distinct scenarios.
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    @tool
    def system_mapping(self, problem_statement: str) -> str:
        """
        Create a high-level system map based on the given problem statement.

        Args:
            problem_statement (str): A description of the problem or situation.

        Returns:
            response (str): A JSON string representing a high-level system map.
        """
        self.notifier.status("Creating system map...")

        provider = AnthropicProvider.from_env()
        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=[],
            system=None
        )

        request_input = f"""
        Based on the following problem statement, create a high-level system map:
        {problem_statement}

        Identify key components, their relationships, and potential feedback loops.
        Return the results as a JSON string with the following structure:
        {{
            "components": [
                {{
                    "name": "Component Name",
                    "description": "Brief description of the component",
                    "connections": ["Component 1", "Component 2", ...]
                }},
                ...
            ],
            "feedback_loops": [
                {{
                    "name": "Loop Name",
                    "description": "Description of the feedback loop",
                    "components_involved": ["Component 1", "Component 2", ...]
                }},
                ...
            ]
        }}
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    @tool
    def risk_assessment(self, problem_statement: str, proposed_solution: str) -> str:
        """
        Perform a risk assessment for the given problem and proposed solution.

        Args:
            problem_statement (str): A description of the problem or situation.
            proposed_solution (str): A description of the proposed solution.

        Returns:
            response (str): A JSON string containing a list of potential risks and their assessments.
        """
        self.notifier.status("Performing risk assessment...")

        provider = AnthropicProvider.from_env()
        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=[],
            system=None
        )

        request_input = f"""
        Perform a risk assessment for the following problem and proposed solution:
        Problem: {problem_statement}
        Proposed Solution: {proposed_solution}

        Identify potential risks, their likelihood, impact, and possible mitigation strategies.
        Return the results as a JSON string with the following structure:
        {{
            "risks": [
                {{
                    "name": "Risk Name",
                    "description": "Description of the risk",
                    "likelihood": "High/Medium/Low",
                    "impact": "High/Medium/Low",
                    "mitigation_strategies": ["Strategy 1", "Strategy 2", ...]
                }},
                ...
            ]
        }}
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    @tool
    def ethical_analysis(self, problem_statement: str, proposed_solution: str) -> str:
        """
        Perform an ethical analysis of the given problem and proposed solution.

        Args:
            problem_statement (str): A description of the problem or situation.
            proposed_solution (str): A description of the proposed solution.

        Returns:
            response (str): A JSON string containing an ethical analysis of the problem and solution.
        """
        self.notifier.status("Performing ethical analysis...")

        provider = AnthropicProvider.from_env()
        exchange = Exchange(
            provider=provider,
            model="claude-3-5-sonnet-20240620",
            messages=[],
            system=None
        )

        request_input = f"""
        Perform an ethical analysis for the following problem and proposed solution:
        Problem: {problem_statement}
        Proposed Solution: {proposed_solution}

        Consider various ethical frameworks and principles, potential ethical dilemmas, and the impact on different stakeholders.
        Return the results as a JSON string with the following structure:
        {{
            "ethical_considerations": [
                {{
                    "principle": "Ethical Principle",
                    "description": "Description of the ethical consideration",
                    "impact": "Positive/Negative/Neutral",
                    "affected_stakeholders": ["Stakeholder 1", "Stakeholder 2", ...],
                    "recommendations": ["Recommendation 1", "Recommendation 2", ...]
                }},
                ...
            ],
            "overall_assessment": "Summary of the ethical analysis and recommendations"
        }}
        """
        response = ask_an_ai(input=request_input, exchange=exchange, no_history=True)
        return response.content[0].text

    def system_prompt(self) -> str:
        """Retrieve instructions on how to use this reasoning tool."""
        return Message.load("prompts/critical_systems_thinking.jinja").text