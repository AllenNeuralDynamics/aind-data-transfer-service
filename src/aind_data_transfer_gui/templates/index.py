"""Defines html index template"""

from jinja2 import Template

template = Template(
    """
<html>
<head>
    <meta charset="UTF-8">
    <title>{% block title %} {% endblock %} AIND Data Transfer Service</title>
    <style>
        nav a {
            color: #d64161;
            font-size: 2em;
            margin-left: 50px;
            text-decoration: none;
        }
    </style>
</head>
<h1> Add a New Upload Job </h1>
<body>
<form method="post" novalidate>
    {{ form.csrf_token }}
    <div>
        {{ form.experiment_type.label }}
        {{ form.experiment_type(placeholder='Experiment Type') }}
        {% if form.experiment_type.errors -%}
        <span>{{ form.experiment_type.errors[0] }}</span>
        {%- endif %}
    </div>
    <div>
        {{ form.acquisition_datetime.label }}
        {{ form.acquisition_datetime(placeholder='Acquisition Datetime') }}
        {% if form.acquisition_datetime.errors -%}
        <span>{{ form.acquisition_datetime.errors[0] }}</span>
        {%- endif %}
    </div>
    <div>
        {{ form.modality.label }}
        {{ form.modality(placeholder='modality') }}
        {% if form.modality.errors -%}
        <span>{{ form.modality.errors[0] }}</span>
        {%- endif %}
    </div>
    <div>
        {{form.source.label}}
        {{ form.source(placeholder='source') }}
        {% if form.source.errors -%}
        <span>{{ form.source.errors[0] }}</span>
        {%- endif %}
    </div>
    <button type="submit">Submit</button>
</form>
</body>
</html>
"""
)
