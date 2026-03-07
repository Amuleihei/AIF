# =====================================================
# TG入口：窑总览
# =====================================================

def handle_kiln_overview(text):

    if text not in ("窑总览", "窑状态总览", "窑概况"):
        return None

    from modules.kiln.kiln_view import build_kiln_overview

    return build_kiln_overview(title="🔥 窑总览", include_footer=True, footer_style="two_lines")
