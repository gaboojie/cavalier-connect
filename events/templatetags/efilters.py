from django import template

register = template.Library()

@register.filter
def has_extension(file_name, extension):
    return file_name.lower().endswith(extension)
