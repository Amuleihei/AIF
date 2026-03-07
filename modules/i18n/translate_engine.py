# =====================================================
# 🌏 AIF 多语言翻译引擎（增强版 · 稳定）
# =====================================================

import re

# -----------------------------------------------------
# 缅文 → 中文（输入翻译）
# -----------------------------------------------------

MM_TO_CN = {

    # 入库
    "ကုန်ပစ္စည်းထည့်": "成品入库",
    "ပစ္စည်းထည့်": "成品入库",

    # 查询
    "သိုလှောင်": "库存",
    "ကုန်ပစ္စည်းစာရင်း": "成品库存",

    # 报表
    "နေ့စဉ်အစီရင်ခံစာ": "日报",
    "အစီရင်ခံစာ": "日报",

    # 原料
    "သစ်သား": "原木",
    "သစ်ဝင်": "原木入库",

    # 发货
    "တင်ပို့": "成品发货",
}


# -----------------------------------------------------
# 中文 → 缅文（输出翻译）
# -----------------------------------------------------

CN_TO_MM = {

    # 📦 库存
    "库存": "သိုလှောင်",
    "库存状态": "သိုလှောင်အခြေအနေ",
    "入库": "သိုလှောင်ထည့်",
    "出库": "သိုလှောင်ထုတ်",
    "成品入库": "ကုန်ချောထည့်",
    "原木入库": "သစ်လုံးထည့်",
    "成品库存": "ကုန်ချောသိုလှောင်",

    # 🪵 原料
    "原料": "ကုန်ကြမ်း",
    "原木": "သစ်လုံး",
    "板材": "ပျဉ်ပြား",

    # 🏭 生产
    "生产": "ထုတ်လုပ်မှု",
    "生产中": "ထုတ်လုပ်နေ",

    # 🔥 窑
    "窑": "မီးဖို",
    "烘干中": "ခြောက်သွေ့နေ",
    "空": "လွတ်",
    "入窑中": "မီးဖိုထည့်နေ",
    "出窑中": "မီးဖိုထုတ်နေ",
    "已完成 待出窑": "ခြောက်ပြီး ထုတ်ရန်စောင့်",
    "已完成": "ပြီးပါပြီ",

    # 📦 成品
    "成品": "ကုန်ချော",
    "成品发货": "ကုန်ချောပို့",

    # 💰 财务
    "财务": "ဘဏ္ဍာရေး",
    "收入": "ဝင်ငွေ",
    "支出": "အသုံးစရိတ်",
    "余额": "လက်ကျန်",

    # 📊 报表
    "日报": "နေ့စဉ်အစီရင်ခံစာ",

    # 🔐 权限
    "权限不足": "ခွင့်ပြုချက်မရှိ",

    # 🧩 系统/通用
    "空指令": "အမိန့်မရှိပါ",
    "未识别指令": "အမိန့်ကို မသိပါ",
    "模块异常": "မော်ဂျူးအမှား",
    "系统错误": "စနစ်အမှား",
    "请联系管理员": "အက်မင်ကို ဆက်သွယ်ပါ",
    "格式": "ပုံစံ",
    "用法": "အသုံးပြုပုံ",
    "示例": "ဥပမာ",
    "完成": "ပြီးပါပြီ",
    "成功": "အောင်မြင်ပါသည်",
    "失败": "မအောင်မြင်ပါ",

    # 🪚/📦 常用字段（尽量覆盖录入回执）
    "上锯": "လွှ",
    "药浸": "ဆေးစိမ်",
    "分拣": "ရွေးချယ်",
    "二次拣选": "ဒုတိယရွေး",
    "投入": "ထည့်သွင်း",
    "产出": "ထွက်ရှိ",
    "托": "ထုပ်",
    "袋": "အိတ်",
    "吨": "တန်",
    "树皮": "သစ်ခေါက်",
    "木渣": "သစ်မှုန့်",
    "锯号": "လွှနံပါတ်",
    "当前": "လက်ရှိ",
    "不足": "မလုံလောက်",
    "需": "လိုအပ်",
    "各工序库存": "လုပ်ငန်းစဉ်အလိုက် သိုလှောင်",
    "无库存": "သိုလှောင်မရှိ",
    "在制": "လုပ်ဆောင်နေ",
    "件": "ခု",
    "工厂状态": "စက်ရုံအခြေအနေ",
    "库存概况": "စတော့အကျဉ်းချုပ်",
    "生产概况": "ထုတ်လုပ်မှုအကျဉ်းချုပ်",
    "窑概况": "မီးဖိုအကျဉ်းချုပ်",
    "窑总览": "မီးဖိုအကျဉ်းချုပ်",
    "系统状态": "စနစ်အခြေအနေ",
    "用户列表": "အသုံးပြုသူစာရင်း",
    "上锯待药浸": "လွှပြီး ဆေးစိမ်စောင့်",
    "药浸待分拣": "ဆေးစိမ်ပြီး ရွေးချယ်စောင့်",
    "分拣待入窑": "ရွေးပြီး မီးဖိုထည့်စောင့်",
    "出窑待二拣": "မီးဖိုထုတ်ပြီး ဒုတိယရွေးစောင့်",
    "待二拣": "ဒုတိယရွေးစောင့်",
    "锯解托": "လွှထုပ်",
    "入窑托": "မီးဖိုထုပ်",
    "药剂累计": "ဆေး စုစုပေါင်း",
    "药剂": "ဆေး",
    "罐次": "ကန်အရေအတွက်",
    "罐数": "ကန်အရေအတွက်",
    "树皮累计": "သစ်ခေါက် စုစုပေါင်း",
    "木渣累计": "သစ်မှုန့် စုစုပေါင်း",
    "二次拣选成品": "ဒုတိယရွေး ကုန်ချော",
    "二次拣选AB": "ဒုတိယရွေး AB",
    "二次拣选BC": "ဒုတိယရွေး BC",
    "二次拣选损耗": "ဒုတိယရွေး ဆုံးရှုံး",
    "无用户": "အသုံးပြုသူမရှိ",
    "无采购记录": "အဝယ်မှတ်တမ်းမရှိ",
    "无订单": "အော်ဒါမရှိ",
    "无预测订单": "ခန့်မှန်းအော်ဒါမရှိ",
    "数值错误": "တန်ဖိုးမှား",
    "现金": "ငွေသား",
    "订单": "အော်ဒါ",
    "运营健康": "လည်ပတ်မှုကောင်း",
    "生产平衡": "ထုတ်လုပ်မှုညီမျှ",
    "用户": "အသုံးပြုသူ",
    "已删除用户": "အသုံးပြုသူ ဖျက်ပြီးပါပြီ",

    # 💰 财务补全
    "今日财务": "ယနေ့ ငွေကြေး",
    "今日收入": "ယနေ့ ဝင်ငွေ",
    "今日统计": "ယနေ့ စာရင်းချုပ်",
    "净额": "စုစုပေါင်း",
    "账户余额": "အကောင့်လက်ကျန်",
    "源账户余额不足": "မူလအကောင့် လက်ကျန်မလုံလောက်",
    "转账": "လွှဲပြောင်း",

    # 📦 库存补全
    "原木库存": "သစ်လုံးသိုလှောင်",
    "原料不足": "ကုန်ကြမ်းမလုံလောက်",
    "已发货": "ပို့ပြီး",
    "未找到": "မတွေ့ပါ",
    "已发过": "ပြီးသားပို့ထား",
    "合计": "စုစုပေါင်း",
    "件数": "ထုပ်အရေအတွက်",
    "根数": "အရေအတွက်",
    "金额": "ပမာဏ",
    "备注": "မှတ်ချက်",
    "规格": "အရွယ်အစား",
    "等级": "အဆင့်",
    "编号": "အမှတ်",
    "区间": "အပိုင်းအခြား",
    "错误": "အမှား",
    "托数错误": "ထုပ်အရေအတွက် အမှား",
    "药剂袋数错误": "ဆေးအိတ် အမှား",
    "袋数错误": "အိတ်အရေအတွက် အမှား",
    "根": "ခု",
    "件": "ခု",

    "为空": "ဗလာ",
}

CN_TO_EN = {
    # =================================================
    # Long phrases first (spacing / readability)
    # =================================================
    "生产日报": "Production Daily Report",
    "工厂日报": "Factory Daily Report",
    "今日生产": "Today's Production",
    "今日台账": "Today's Ledger",
    "上锯投入": "Saw input",
    "上锯产出": "Saw output",
    "出窑均产": "Unload avg",
    "待二拣": "Pending 2nd sort",
    "开始烘干/烘干中": "Started drying/Drying",
    "开始烘干": "Started drying",
    "烘干完成待出": "Dry complete, waiting unload",
    "上次": "Last",

    # 🧩 System/common
    "空指令": "Empty command",
    "未识别指令": "Unknown command",
    "模块异常": "Module error",
    "系统错误": "System error",
    "请联系管理员": "Please contact admin",
    "格式": "Format",
    "用法": "Usage",
    "示例": "Example",
    "完成": "Completed",
    "成功": "Success",
    "失败": "Failed",
    "为空": "empty",
    "数值错误": "Invalid number",
    "错误": "Error",
    "金额": "amount",
    "备注": "note",
    "规格": "spec",
    "等级": "grade",
    "编号": "code",
    "区间": "range",
    "托数错误": "Invalid pallet count",
    "药剂袋数错误": "Invalid chemical bag count",
    "袋数错误": "Invalid bag count",
    "权限不足": "Permission denied",

    # 📦 Inventory/production terms
    "库存状态": "Stock Status",
    "库存概况": "Stock Overview",
    "库存": "Stock",
    "入库": "In",
    "出库": "Out",
    "原料": "Raw",
    "原木": "Logs",
    "原木入库": "Log In",
    "原木库存": "Log Stock",
    "原料不足": "Insufficient raw",
    "生产": "Production",
    "生产中": "In production",
    "在制": "WIP",
    "在制不足": "Insufficient WIP",
    "投入": "Input",
    "产出": "Output",
    "托": "pallet",
    "袋": "bag",
    "根": "pcs",
    "件": "pcs",
    "吨": "MT",
    "树皮": "Bark",
    "木渣": "Sawdust",
    "锯号": "Saw#",
    "上锯": "Saw",
    "药浸": "Dip",
    "分拣": "Sort",
    "拣选": "Sort",
    "二次拣选": "2nd Sort",
    "工序库存": "Process Stock",
    "各工序库存": "Process Stock",
    "上锯待药浸": "Saw→Dip (pending)",
    "药浸待分拣": "Dip→Sort (pending)",
    "分拣待入窑": "Sort→Kiln (pending)",
    "出窑待二拣": "Kiln→2nd sort (pending)",
    "锯解托": "Saw pallet",
    "入窑托": "Kiln pallet",
    "药剂累计": "Chem total",
    "药剂": "Chemical",
    "罐次": "tanks",
    "罐数": "tanks",
    "树皮累计": "Bark total",
    "木渣累计": "Sawdust total",
    "二次拣选成品": "2nd sort products",
    "二次拣选AB": "2nd sort AB",
    "二次拣选BC": "2nd sort BC",
    "二次拣选损耗": "2nd sort loss",
    "无库存": "No stock",

    # 🔥 Kiln
    "窑": "Kiln",
    "窑状态": "Kiln Status",
    "入窑": "Load",
    "点火": "Fire",
    "出窑": "Unload",
    "空": "Empty",
    "烘干中": "Drying",
    "入窑中": "Loading",
    "出窑中": "Unloading",
    "已完成 待出窑": "Ready to unload",
    "已完成": "Completed",

    # 📦 Product
    "成品": "Product",
    "成品入库": "Product In",
    "成品库存": "Product Stock",
    "成品发货": "Ship",
    "已发货": "Shipped",
    "未找到": "Not found",
    "已发过": "Already shipped",
    "合计": "Total",
    "件数": "Packages",
    "根数": "Pieces",
    "体积": "Volume",

    # 💰 Finance
    "财务": "Finance",
    "财务概况": "Finance Overview",
    "财务明细": "Finance Details",
    "收入": "Income",
    "支出": "Expense",
    "余额": "Balance",
    "今日财务": "Today's Finance",
    "净额": "Net",
    "总额": "Total",
    "账户余额": "Account Balance",
    "余额不足": "Insufficient balance",
    "源账户余额不足": "Insufficient source balance",
    "转账": "Transfer",

    # Reports/menus
    "日报": "Daily Report",
    "窑概况": "Kiln Overview",
    "窑总览": "Kiln Overview",
    "老板端仅支持查询，请点击菜单按钮。": "Boss view is read-only. Please use menu buttons.",
    "老板这里暂不支出闲聊哦~": "Boss view is read-only.",
}


# =====================================================
# ⭐ 缅文 → 中文（输入处理）
# =====================================================

def translate_to_cn(text: str) -> str:
    # saw number (English): saw#3 / saw3 / saw 3
    text = re.sub(r"\b(saw)\s*#?\s*([1-6])\b", r"锯号\2", text, flags=re.I)

    normalized = text.strip()
    lower = normalized.lower()

    nums = re.findall(r"-?\d+(?:\.\d+)?", normalized)

    # -------------------------------------------------
    # 0) 前缀替换（保留参数，便于现场录入）
    # -------------------------------------------------
    prefix_map = [
        # 查询类（长词优先，避免被短前缀截断）
        ("မီးဖိုအခြေအနေ", "窑状态"),
        ("အဆင့်သိုလှောင်", "工序库存"),
        ("ပရင်တာစာရင်း", "打印机列表"),
        ("ပုံနှိပ်စမ်း", "打印测试"),
        ("နေ့စဉ်အစီရင်ခံစာပုံနှိပ်", "打印日报"),
        ("နေ့စဉ်ထုတ်လုပ်မှုစာရင်းပုံနှိပ်", "打印今日台账"),
        ("ရွေးစာရင်း", "分拣编号"),
        ("ဒုတိယရွေးမှတ်တမ်း", "二次拣选记录"),
        ("ဒုတိယ ရွေး မှတ်တမ်း", "二次拣选记录"),
        ("နေ့စဉ်ထုတ်လုပ်မှုစာရင်း", "今日台账"),
        ("လွှအဖွဲ့စာရင်း", "锯工组统计"),
        ("ယနေ့လွှအဖွဲ့", "锯工组统计"),
        ("အသုံးပြုသူစာရင်း", "用户列表"),
        ("ဝန်ထမ်းထည့်", "添加用户"),
        ("ဝန်ထမ်းဖျက်", "删除用户"),
        # 生产主链
        ("သစ်ဝင်", "原木入库"),
        ("ဆေးစိမ်", "药浸"),
        ("ဒုတိယ ရွေး", "二次拣选"),
        ("ဒုတိယရွေး", "二次拣选"),
        ("ရွေး", "分拣"),
        ("လွှ", "上锯"),
    ]
    for mm_prefix, cn_prefix in prefix_map:
        if normalized.startswith(mm_prefix):
            return cn_prefix + normalized[len(mm_prefix):]
        if normalized == mm_prefix:
            return cn_prefix

    if normalized.startswith("ပရင်တာသတ်မှတ်"):
        return "设置打印机 " + normalized[len("ပရင်တာသတ်မှတ်"):].strip()

    # 缅语单锯查询（例：2号锯统计 / 2နံပါတ်လွှ စာရင်း）
    m_saw_single = re.fullmatch(
        r"\s*([1-6])\s*(?:号锯|锯号|နံပါတ်လွှ|စက်လွှ)?\s*(?:统计|数据|产值|စာရင်း|အချက်အလက်)?\s*",
        normalized
    )
    if m_saw_single and ("锯" in normalized or "လွှ" in normalized):
        return f"{m_saw_single.group(1)}号锯统计"

    # 标准中文命令直接放行，避免翻译层二次改写导致参数丢失
    if normalized.startswith((
        "强制",
        "上锯",
        "药浸",
        "分拣",
        "拣选",
        "二次拣选",
        "待入窑导出",
        "分拣导出",
        "原木入库",
        "成品入库",
        "树皮",
        "木渣",
        "锯工组统计",
        "锯号",
    )):
        return normalized

    # SCM/业务命令已是标准中文，避免被财务自然语言误判
    if normalized.startswith(("采购 ", "添加供应商 ", "到货 ", "客户订单 ")):
        return normalized
    if normalized in ("采购", "采购列表"):
        return normalized

    # -------------------------------------------------
    # ① 精确词典替换（放在前缀识别后，避免误伤长命令）
    # -------------------------------------------------
    for mm, cn in MM_TO_CN.items():
        if mm in text:
            text = text.replace(mm, cn)
    normalized = text.strip()
    lower = normalized.lower()
    nums = re.findall(r"-?\d+(?:\.\d+)?", normalized)

    # -------------------------------------------------
    # ② 模糊匹配（现场容错）
    # -------------------------------------------------

    # ===== 工序主链（中/缅/英）=====
    # 上锯 3 2
    if (
        ("上锯" in normalized)
        or ("လွှ" in normalized)
        or ("saw" in lower)
    ) and len(nums) >= 2:
        if len(nums) >= 4:
            return f"上锯 {nums[0]} {nums[1]} {nums[2]} {nums[3]}"
        if len(nums) >= 3:
            return f"上锯 {nums[0]} {nums[1]} {nums[2]}"
        return f"上锯 {nums[0]} {nums[1]}"

    # 药浸 罐次 [托数] [药剂袋数]
    if (
        ("药浸" in normalized)
        or ("ဆေးစိမ်" in normalized)
        or ("dip" in lower)
    ) and len(nums) >= 1:
        if len(nums) >= 3:
            return f"药浸 {nums[0]} {nums[1]} {nums[2]}"
        if len(nums) >= 2:
            return f"药浸 {nums[0]} {nums[1]}"
        return f"药浸 {nums[0]}"

    # 二次拣选 6 1.8 1.0 0.8
    if (
        (("ဒုတိယ" in normalized) and ("ရွေး" in normalized))
        or ("second sort" in lower)
    ) and len(nums) >= 4:
        return f"二次拣选 {nums[0]} {nums[1]} {nums[2]} {nums[3]}"

    # 分拣 20260301-01 84 294 / 分拣 84 294 1
    if (
        ("分拣" in normalized)
        or ("拣选" in normalized)
        or ("ရွေး" in normalized)
        or ("select" in lower)
        or ("sorting" in lower)
    ) and ("二次" not in normalized) and ("ဒုတိယ" not in normalized) and len(nums) >= 1:
        parts = normalized.split()
        # 中文分拣命令直接放行
        if parts and parts[0] in ("分拣", "拣选"):
            parts[0] = "分拣"
            return " ".join(parts)
        return f"分拣 {normalized.replace('ရွေး', '').replace('select', '').replace('sorting', '').strip()}"

    # 原木入库（缅文模糊）
    if lower.startswith(("log in", "logs in", "log stock in", "logs stock in")) and nums:
        return f"原木入库 {nums[0]}"
    if match_keywords(text, ["သစ်", "ထည့်"]):
        if nums:
            return f"原木入库 {nums[0]}"
        return "原木入库"

    # 成品入库
    if match_keywords(text, ["ကုန်", "ထည့်"]):
        return "成品入库"

    # 窑状态（缅语/英文）
    if ("မီးဖို" in normalized and "အခြေအနေ" in normalized) or ("kiln status" in lower):
        return "窑状态"

    # 锯工组统计（缅语）
    if ("လွှ" in normalized and ("အဖွဲ့" in normalized or "စု" in normalized) and ("စာရင်း" in normalized or "ယနေ့" in normalized)):
        return "锯工组统计"

    # 工序库存（缅语）
    if ("အဆင့်" in normalized and "သိုလှောင်" in normalized) or ("process stock" in lower):
        return "工序库存"

    # 待入窑导出（英文）
    if ("export" in lower or "dump" in lower) and ("kiln" in lower and "load" in lower):
        kid = None
        m_k = re.search(r"\b([ABCD])\b", normalized, re.I)
        if m_k:
            kid = m_k.group(1).upper()
        nums2 = [n for n in re.findall(r"\b(\d+)\b", normalized)]
        per_line = nums2[0] if len(nums2) >= 1 else None
        limit = nums2[1] if len(nums2) >= 2 else None
        out = "待入窑导出"
        if kid:
            out += f" {kid}"
        if per_line:
            out += f" {per_line}"
        if limit:
            out += f" {limit}"
        return out

    # 待入窑导出（缅语，推荐关键词：မီးဖို + ထည့် + စာရင်း + ထုတ်）
    if ("မီးဖို" in normalized) and match_keywords(normalized, ["ထည့်", "စာရင်း", "ထုတ်"]):
        kid = None
        m_k = re.search(r"\b([ABCD])\b", normalized, re.I)
        if m_k:
            kid = m_k.group(1).upper()
        nums2 = [n for n in re.findall(r"\b(\d+)\b", normalized)]
        per_line = nums2[0] if len(nums2) >= 1 else None
        limit = nums2[1] if len(nums2) >= 2 else None
        out = "待入窑导出"
        if kid:
            out += f" {kid}"
        if per_line:
            out += f" {per_line}"
        if limit:
            out += f" {limit}"
        return out

    # 库存查询
    if lower in (
        "product stock",
        "product inventory",
        "products stock",
        "products inventory",
        "finished goods",
        "finished goods stock",
        "finished goods inventory",
        "finished stock",
        "fg stock",
        "fg inventory",
    ):
        return "成品库存"
    if lower.startswith(("product stock", "product inventory", "finished goods", "fg stock", "fg inventory")) and not nums:
        return "成品库存"

    if lower in ("stock", "inventory") or normalized == "库存":
        return "库存"

    # 成品编号列表（英文）
    if lower in ("product codes", "product list", "product code list", "product code") and not nums:
        return "成品编号"

    # 日报
    if lower in ("report", "daily report", "daily") or normalized == "日报":
        return "日报"

    # 对账
    if lower in ("reconcile", "reconcile report", "reconciliation", "check") and not nums:
        return "对账"

    # 概况类查询（英文）
    if lower in ("stock overview", "inventory overview") and not nums:
        return "库存概况"
    if lower in ("production overview",) and not nums:
        return "生产概况"
    if lower in ("finance overview",) and not nums:
        return "财务概况"
    if lower in ("finance details", "finance detail", "finance records", "finance transactions") and not nums:
        return "财务明细"
    if lower in ("kiln overview", "kiln summary") and not nums:
        return "窑总览"
    if lower in ("factory status", "factory dashboard", "dashboard") and not nums:
        return "工厂状态"

    # 发货
    if lower in ("ship", "send") or normalized == "发货":
        return "成品发货"

    # 财务（英文快捷命令）
    if lower.startswith("income ") and len(normalized.split()) >= 2:
        return "收入 " + normalized.split(" ", 1)[1].strip()
    if lower.startswith("expense ") and len(normalized.split()) >= 2:
        return "支出 " + normalized.split(" ", 1)[1].strip()
    if lower.startswith("transfer ") and len(normalized.split()) >= 2:
        return "转账 " + normalized.split(" ", 1)[1].strip()
    if lower in ("balance", "account balance") and not nums:
        return "余额"
    if lower in ("today finance", "today income") and not nums:
        return "今日财务"

    # -------------------------------------------------
    # ⭐ ③ 财务自然语言解析（核心）
    # -------------------------------------------------

    # 中文支出
    if re.search(r"(支出|花|买|采购|费用|开销|付|用了)", text):
        m = re.search(r"(\d+(\.\d+)?)", text)
        if m:
            return f"支出 {m.group(1)}"

    # 中文收入
    if re.search(r"(收入|收款|卖|销售|进账|到账)", text):
        m = re.search(r"(\d+(\.\d+)?)", text)
        if m:
            return f"收入 {m.group(1)}"

    # 缅文支出
    if re.search(r"(ဝယ်|အသုံး|ကုန်ကျ|ပေး)", text):
        m = re.search(r"(\d+(\.\d+)?)", text)
        if m:
            return f"支出 {m.group(1)}"

    # 缅文收入
    if re.search(r"(ရောင်း|ဝင်ငွေ|လက်ခံ)", text):
        m = re.search(r"(\d+(\.\d+)?)", text)
        if m:
            return f"收入 {m.group(1)}"

    # -------------------------------------------------
    return text


# =====================================================
# ⭐ 中文 → 缅文（输出翻译）
# =====================================================

def translate_from_cn(text: str, lang: str = "my") -> str:
    """
    Translate canonical Chinese outputs to the given language.
    Supported: my (Burmese), en (English). Fallback: return original text.
    """
    code = (lang or "my").strip().lower()
    table = CN_TO_MM if code == "my" else CN_TO_EN if code == "en" else None
    if not table:
        return text

    # Classifier-aware replacements (avoid "2罐" -> "2tank")
    if code in ("en", "my"):
        def _tank_repl(m: re.Match) -> str:
            n = int(m.group(1))
            if code == "en":
                unit = "tank" if n == 1 else "tanks"
                return f"{n} {unit}"
            return f"{n} ကန်"

        text = re.sub(r"(\d+)\s*罐", _tank_repl, text)

        def _bag_repl(m: re.Match) -> str:
            n = int(m.group(1))
            if code == "en":
                unit = "bag" if n == 1 else "bags"
                return f"{n} {unit}"
            return f"{n} အိတ်"

        text = re.sub(r"(\d+)\s*袋", _bag_repl, text)

        def _pallet_repl(m: re.Match) -> str:
            n = int(m.group(1))
            if code == "en":
                unit = "pallet" if n == 1 else "pallets"
                return f"{n} {unit}"
            return f"{n} ထုပ်"

        text = re.sub(r"(\d+)\s*托", _pallet_repl, text)
        if code == "en":
            def _remain_pallet_repl(m: re.Match) -> str:
                n = int(m.group(1))
                unit = "pallet" if n == 1 else "pallets"
                return f"remaining {n} {unit}"

            text = re.sub(r"剩\s*(\d+)\s*(pallet|pallets)\b", _remain_pallet_repl, text)
        else:
            text = re.sub(r"剩\s*(\d+)\s*(?:ထုပ်)\b", r"ကျန် \1 ထုပ်", text)

        def _kiln_tag_repl(m: re.Match) -> str:
            kid = m.group(1).upper()
            if code == "en":
                return f"Kiln {kid}"
            return f"{kid}မီးဖို"

        text = re.sub(r"\b([ABCD])\s*窑", _kiln_tag_repl, text, flags=re.I)

        def _kiln_count_repl(m: re.Match) -> str:
            n = int(m.group(1))
            if code == "en":
                unit = "kiln" if n == 1 else "kilns"
                return f"{n} {unit}"
            return f"{n} မီးဖို"

        text = re.sub(r"(\d+)\s*窑", _kiln_count_repl, text)

        def _remain_repl(m: re.Match) -> str:
            h = int(m.group(1))
            if code == "en":
                return f"remaining {h}h"
            return f"ကျန် {h}h"

        text = re.sub(r"剩\s*(\d+)\s*h\b", _remain_repl, text)

        if code == "en":
            text = (
                text.replace("运行:", "Running:")
                .replace("总托:", "Total pallets:")
                .replace("：", ":")
                .replace("（", "(")
                .replace("）", ")")
            )
            text = re.sub(r"(Kiln\s+[A-D]):(?=\S)", r"\1: ", text)
        else:
            text = (
                text.replace("运行:", "လုပ်ဆောင်နေ:")
                .replace("总托:", "ထုပ် စုစုပေါင်း:")
                .replace("：", ":")
                .replace("（", "(")
                .replace("）", ")")
            )
            text = re.sub(r"([A-D]မီးဖို):(?=\S)", r"\1: ", text)

    # Longest-first to avoid partial replacements (e.g., "成品入库" vs "入库")
    for cn in sorted(table.keys(), key=len, reverse=True):
        if cn in text:
            text = text.replace(cn, table[cn])

    # Small post-fixes for readability (after CN->EN replacements)
    if code == "en":
        text = re.sub(r"\bLast(?=\d)", "Last ", text)
        text = re.sub(r"\bChemical:(?=\d)", "Chemical: ", text)
    return text


# =====================================================
# ⭐ 工具函数
# =====================================================

def match_keywords(text, words):

    return all(w in text for w in words)
