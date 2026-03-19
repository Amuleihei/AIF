# i18n 聚合入口：统一导出 LANGUAGES，供业务代码引用
from .zh import TEXTS as ZH_TEXTS
from .en import TEXTS as EN_TEXTS
from .my import TEXTS as MY_TEXTS

LANGUAGES = {
    'zh': ZH_TEXTS,
    'en': EN_TEXTS,
    'my': MY_TEXTS,
}

__all__ = ['LANGUAGES']
