{% macro title_case(column) %}
    array_to_string(
        list_transform(
            str_split(lower(trim({{ column }})), ' '),
            x -> upper(x[1:1]) || substr(x, 2)
        ),
        ' '
    )
{% endmacro %}
