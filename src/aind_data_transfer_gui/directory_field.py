"""Custom WTForms Field for selecting a directory"""
from wtforms.fields import StringField
from wtforms.widgets import TextInput


class DirectoryInput(TextInput):
    """Custom widget to select directory"""

    input_type = "file"
    directory_only = True

    def __call__(self, field, **kwargs):
        """enables directory selection in browser"""
        kwargs.setdefault("type", self.input_type)
        if self.directory_only:
            kwargs["webkitdirectory"] = True
            kwargs["mozdirectory"] = True
            kwargs["directory"] = True
        return super().__call__(field, **kwargs)


class DirectoryField(StringField):
    """Gets source path as string"""
    widget = DirectoryInput()
