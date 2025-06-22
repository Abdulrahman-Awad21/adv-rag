import os
from string import Template

class TemplateParser:

    def __init__(self, language: str=None, default_language='en'):
        self.current_path = os.path.dirname(os.path.abspath(__file__))
        self.default_language = default_language
        self.language = None
        self.set_language(language)
    
    def set_language(self, language: str):
        if not language:
            self.language = self.default_language

        language_path = os.path.join(self.current_path, "locales", language)
        if os.path.exists(language_path):
            self.language = language
        else:
            self.language = self.default_language

    def get(self, group: str, key: str, vars: dict={}):
        if not group or not key:
            return None
        
        group_path = os.path.join(self.current_path, "locales", self.language, f"{group}.py" )
        targeted_language = self.language
        if not os.path.exists(group_path):
            group_path = os.path.join(self.current_path, "locales", self.default_language, f"{group}.py" )
            targeted_language = self.default_language

        if not os.path.exists(group_path):
            return None
        
        module = __import__(f"stores.llm.templates.locales.{targeted_language}.{group}", fromlist=[group])

        if not module:
            return None
        
        key_attribute = getattr(module, key)
        
        # Check if the retrieved attribute is a dictionary (for structured prompts)
        if isinstance(key_attribute, dict):
            substituted_dict = {}
            for sub_key, template_string in key_attribute.items():
                if isinstance(template_string, str):
                    template_obj = Template(template_string)
                    substituted_dict[sub_key] = template_obj.safe_substitute(vars)
                else:
                    substituted_dict[sub_key] = template_string # Preserve non-string values
            return substituted_dict
        
        # Check if it's a Template object (for simple string prompts)
        elif isinstance(key_attribute, Template):
            return key_attribute.safe_substitute(vars)
        
        # Fallback for unexpected types
        return None