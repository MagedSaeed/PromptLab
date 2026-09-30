import json
import logging
import os
import time

import anthropic
import jinja2
from datasets import load_dataset
from google import genai
from google.genai import types
from jinja2 import Environment, StrictUndefined
from openai import OpenAI

logging.getLogger("datasets").setLevel(logging.ERROR)


class Template:
    def __init__(self, name, text, example, answer_choices):

        self.name = name
        self.text = text
        self.example = example
        self.valid = True
        self.msg = ""
        self.answer_choices = answer_choices
        self.applied_template = ""
        self.valid, self.msg = self.validate_template()

    def validate_template(self):
        try:
            self.applied_template = self.test_template()
        except:
            return False, "invalid template"

        if "|||" not in self.text:
            return False, "invalid no |||"

        # check answer choices
        if self.answer_choices:
            answers = self.applied_template.split("|||")[-1].strip()
            for answer in answers.split(","):
                if answer.strip() not in self.answer_choices:
                    return False, "invalid output"

        return True, ""

    def test_template(self):
        env = Environment(undefined=StrictUndefined)
        # Load your template
        template = env.from_string(self.text)

        # Render the template with the variables
        rendered_template = template.render(
            self.example, answer_choices=self.answer_choices
        )
        return rendered_template


class TemplateCreator:

    def __init__(self, dataset_name, config=None, lang="English", answer_choices=[]):
        self.chatgpt_client = OpenAI(api_key=os.environ["chatgpt_key"])
        self.claude_client = anthropic.Anthropic(api_key=os.environ["claude_key"])
        self.gemini_client = genai.Client(api_key=os.environ["gemini_key"])
        self.lang = lang
        if config:
            self.dataset = load_dataset(dataset_name, config, trust_remote_code=True)
        else:
            self.dataset = load_dataset(dataset_name, trust_remote_code=True)

        self.split = "train"
        if "train" in self.dataset:
            self.split = "train"
        elif "validation" in self.dataset:
            self.split = "validation"
        else:
            self.split = "test"
        self.sample = self.dataset[self.split][0]
        self.schema = self.get_schema()
        self.example = {c: self.sample[c] for c in self.schema}
        self.answer_choices = answer_choices

        self.system_prompt_answer_choices = f"""
    You are a prompt template creator. Given a task, dataset schema. You should create a template for a the task.
    Can you provide some examples of answer choices for such task? Please provide the answer choices as a python list.
    Do NOT print any other text.
    """

    def get_system_prompt(self, num_templates=5):
        return f"""
    You are a prompt template creator. Given a task, dataset schema, and answer_choices.
    You should create a template using jinja that can be applied to an example in the dataset.
    The prompt and completion are separated by |||. You should create {num_templates} different templates in {self.lang} language as a json with a key that represents each template content.
    Please choose creative templates with enough variation. The order of the jinja variables can be changed. 
    Do Not use a general name of the template like "template", USE more representative name. 
    Do NOT print any other text except the json. Do NOT use any integer features. If there are answer_choices, use as is do NOT change.
    If there are answer_choices use the variable as is, do NOT introduce any new answer choices.
    All the jinja variables must be from the schema. Do NOT introduce new variable names.  
    If the answer_choices in the example template exist use it in the completion without any changes. 
    This is an important test. Please respect all the mentioned points. 
    """

    def get_schema(self):
        schema = {}
        features = self.dataset[self.split].features
        for feature_name in features:
            feature = features[feature_name]
            if type(feature) == list:
                try:
                    schema[feature_name] = feature[0].dtype
                except:
                    continue
            elif type(feature) == dict:
                first_feature_key = list(feature.keys())[0]
                schema[feature_name] = feature[first_feature_key]
            else:
                try:
                    schema[feature_name] = feature.names
                except:
                    schema[feature_name] = feature.dtype
        return schema

    def get_prompt(self, task_name, example_template):
        if self.answer_choices:
            return f"""
      Task: {task_name}
      Dataset Schema: {self.schema}
      Answer Choices: {self.answer_choices}
      Example: {self.example}
      Example Template: {example_template}
      """
        else:
            return f"""
      Task: {task_name}
      Dataset Schema: {self.schema}
      Example: {self.example}
      Example Template: {example_template}
      """

    def clean(self, out):
        return out.replace("```", "").replace("json", "")

    def prompt_chatgpt(
        self, task_name, example_template, version="gpt-4-turbo", num_templates=5
    ):

        out_templates = []
        num_invalid_templates = 0
        num_valid_templates = 0

        while num_valid_templates < num_templates:
            time.sleep(0.1)
            if num_invalid_templates > 5:
                print(self.dataset)
                print("max retries")
                break
            if len(self.answer_choices) < 0:
                message = self.chatgpt_client.chat.completions.create(
                    model=version,
                    messages=[
                        {
                            "role": "system",
                            "content": self.system_prompt_answer_choices,
                        },
                        {
                            "role": "user",
                            "content": self.get_prompt(task_name, example_template),
                        },
                    ],
                )
                try:
                    self.answer_choices = eval(message.choices[0].message.content)
                    assert type(self.answer_choices) == list
                except:
                    print("Not correct format ", message.choices[0].message.content)
                    return []
            message = self.chatgpt_client.chat.completions.create(
                model=version,
                messages=[
                    {
                        "role": "system",
                        "content": self.get_system_prompt(num_templates=num_templates),
                    },
                    {
                        "role": "user",
                        "content": self.get_prompt(task_name, example_template),
                    },
                ],
            )
            try:
                generated_templates = json.loads(
                    self.clean(message.choices[0].message.content)
                )
            except:
                print("incorrect json format")
                continue

            if len(generated_templates) > num_templates:
                print("wrong number of tempaltes")
                continue

            for template in generated_templates:
                template = Template(
                    template,
                    generated_templates[template],
                    self.example,
                    self.answer_choices,
                )
                out_templates.append(template)
                if template.valid:
                    num_valid_templates += 1
                else:
                    num_invalid_templates += 1

                if num_valid_templates >= num_templates:
                    break
        return out_templates

    def prompt_claude(
        self, task_name, example_template, version="claude-3-5-sonnet-20240620"
    ):
        print(version)
        message = self.claude_client.messages.create(
            model=version,
            max_tokens=1000,
            system=self.system_prompt_answer_choices,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.get_prompt(task_name, example_template),
                        }
                    ],
                }
            ],
        )
        self.answer_choices = eval(message.content[0].text)
        assert type(self.answer_choices) == list
        message = self.claude_client.messages.create(
            model=version,
            max_tokens=1000,
            system=self.system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self.get_prompt(task_name, example_template),
                        }
                    ],
                }
            ],
        )
        templates = json.loads(self.clean(message.content[0].text))
        return templates

    def prompt_gemini(self, task_name, example_template):
        response = self.gemini_client.models.generate_content(
            model="gemini-1.5-pro",
            contents=self.get_prompt(task_name, example_template),
            config=types.GenerateContentConfig(
                system_instruction=self.system_prompt_answer_choices
            ),
        )
        try:
            self.answer_choices = eval(response.text)
            assert type(self.answer_choices) == list
        except:
            print("Not correct format ", response.text)
        return []

    def apply_template(self, template):
        template = jinja2.Template(template)
        return template.render(self.example, answer_choices=self.answer_choices)

    def apply_templates(self, templates):
        applied_templates = {}
        for template_name in templates:
            template = templates[template_name]
            result = self.apply_template(template)
            applied_templates[template_name] = result
        return applied_templates
