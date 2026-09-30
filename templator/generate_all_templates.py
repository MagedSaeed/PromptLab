import logging
import os

import pandas as pd
from main import TemplateCreator
from tqdm import tqdm
from utils import get_dataset_info

logging.getLogger("datasets").setLevel(logging.ERROR)

template_names = []
templates = []
applied_templates = []
datasets = []
msgs = []

for i in tqdm(range(84)):
    dataset_name, subset, task_name, example_template, answer_choices = (
        get_dataset_info(i)
    )
    t = TemplateCreator(dataset_name, config=subset, answer_choices=answer_choices)
    generated_templates = t.prompt_chatgpt(
        task_name, example_template, version="gpt-4o", num_templates=1
    )
    if len(generated_templates):
        for template in generated_templates:
            datasets.append(dataset_name)
            templates.append(template.text)
            applied_templates.append(template.applied_template)
            template_names.append(template.name)
            msgs.append(template.msg)
    else:
        datasets.append(dataset_name)
        templates.append("")
        applied_templates.append("")
        template_names.append("")
        msgs.append("")


pd.DataFrame(
    {
        "dataset_name": datasets,
        "template_name": template_names,
        "template": templates,
        "applied_template": applied_templates,
        "msgs": msgs,
    }
).to_csv("results_gpt4_turbo.csv")
