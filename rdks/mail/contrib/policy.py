from email.policy import EmailPolicy
from .contentmanager import ContentManager
from .headerregistry import HeaderRegistry

__all__ = [
    'default', 'strict', 'SMTP', 'HTTP',
]

default = EmailPolicy(
    header_factory=HeaderRegistry(),
    content_manager=ContentManager())
strict = default.clone(raise_on_defect=True)
SMTP = default.clone(linesep='\r\n')
HTTP = default.clone(linesep='\r\n', max_line_length=None)
SMTPUTF8 = SMTP.clone(utf8=True)
