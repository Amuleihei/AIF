def _lang_pack(lang: str) -> dict:
    lc = str(lang or "zh").strip().lower()
    if lc == "en":
        return {
            "stage_front": "Front Stage (Sawing / Dipping)",
            "stage_middle": "Middle Stage (Sorting / Kiln In / Kiln Out)",
            "stage_middle_load": "Middle Stage (Sorting / Kiln Loading Pace)",
            "stage_back": "Back Stage (Secondary Sort / Finished Goods / Shipping)",
            "stage_back_carry": "Back Stage (Secondary Sort / Kiln-Out Handover / Finished Push)",
            "weakest_default": "Middle Stage",
            "weakest_reason": "The system currently sees this stage as the weakest by score.",
            "symptom_label": "Current pressure stage",
            "root_label": "Priority improvement stage",
            "root_bottleneck_reply": "Conclusion: the stage that deserves priority improvement is more likely \"{root}\".",
            "root_bottleneck_basis": "Basis: {reason}",
            "symptom_reply": "Symptom: the most visible slowdown is currently showing up in {symptom}.",
            "second_reply": "Comparison: the second weakest stage is {name}, score {score}.",
            "advice_root_first": "Advice: pull the priority improvement stage upward first, then see whether the surface symptom eases on its own.",
            "adjust_reply": "Conclusion: the first stage to raise now is \"{root}\".",
            "adjust_basis": "Basis: {reason}",
            "adjust_advice": "Advice: first restore the priority improvement stage to a healthy pace, then watch whether the pressure stage improves naturally.",
            "generic_title": "Conclusion: follow the priority improvement stage first instead of chasing surface symptoms.",
            "generic_basis": "Basis:",
            "generic_top_score": "- End-to-end score {score}",
            "generic_bottleneck": "- Current pressure stage {name}: {reason}",
            "generic_root": "- Priority improvement stage {name}: {reason}",
            "generic_second": "- Second weakest stage {name}: {reason}",
            "generic_advice": "Advice:\n1. Raise the priority improvement stage first.\n2. Watch whether the pressure stage stabilizes naturally.\n3. Then fine-tune upstream and downstream pace.",
            "context_title": "Live operating data:",
            "context_log_stock": "- Log stock: {value} MT",
            "context_saw_stock": "- Sawing stock: {value} trays",
            "context_dip_stock": "- Dipping stock: {value} trays",
            "context_sorting_stock": "- Pending kiln stock: {value} trays",
            "context_kiln_done_stock": "- Pending secondary-sort stock: {value} trays",
            "context_product_stock": "- Finished stock: {count} pcs / {m3} m3",
            "context_ship_ygn": "- On the way to Yangon: {value} orders",
            "context_ship_arrived": "- Arrived at Yangon warehouse: {value} orders",
            "context_ship_departed": "- Departed from Yangon port: {value} orders",
            "context_system_summary": "- Full-system summary:",
            "context_total_score": "  - End-to-end score: {value}",
            "context_front_score": "  - Front-stage score: {value}",
            "context_middle_score": "  - Middle-stage score: {value}",
            "context_back_score": "  - Back-stage score: {value}",
            "context_symptom_stage": "  - Current pressure stage: {value}",
            "context_symptom_reason": "  - Pressure explanation: {value}",
            "context_root_stage": "  - Priority improvement stage: {value}",
            "context_root_reason": "  - Improvement explanation: {value}",
            "context_ratio_dip_vs_saw": "  - Today's dip/saw ratio: {value}%",
            "context_ratio_sort_vs_dip": "  - Today's sort/dip ratio: {value}%",
            "context_ratio_secondary_vs_sort": "  - Today's secondary/sort ratio: {value}%",
            "context_ratio_product_vs_secondary": "  - Today's finished/secondary ratio: {value}%",
            "context_kilns": "- Kiln status:",
            "overview_total": "Total {value}",
            "overview_front": "Front {value}",
            "overview_middle": "Middle {value}",
            "overview_back": "Back {value}",
            "overview_kiln_abnormal": "Kiln anomalies {value}",
            "brief": "The stage that most needs improvement is likely \"{root}\", while current pressure is showing up mainly in \"{symptom}\".",
            "recommendation_1": "Put the first improvement push on \"{root}\" instead of reacting only to the surface symptom.",
            "recommendation_2": "If the symptom is showing around the kiln, first inspect kiln-out handover, secondary sorting, and finished push instead of blaming the kiln itself.",
            "recommendation_3": "If too many kilns are empty, trace upstream supply and kiln-loading handoff before deciding whether to change sawing or dipping pace.",
            "root_back_reason": "The symptom is visible around the kiln, but the root cause is more likely after kiln-out. Ready/unloading overdue kilns: {overdue}; pending secondary-sort stock is only {stock}, so this looks less like slow kiln processing and more like weak kiln-out handover, secondary sorting, or finished push.",
            "root_front_reason": "There are {empty} empty kilns and only {sorting} pending kiln trays, which means the kiln front is short of material. Dipping stock is {dip} trays and today's dip/saw ratio is {ratio}%, so the root cause looks more like insufficient upstream supply.",
            "root_middle_reason": "There are {empty} empty kilns, but sawing stock is still {saw} trays, so this is not a total material shortage. It looks more like weak handoff from dipping into sorting and kiln loading, with only {sorting} pending kiln trays.",
            "root_middle_load_reason": "Pending kiln stock is up to {sorting} trays, which means upstream has already pushed material forward, but kiln-loading pace has not kept up. This points more to limited digestion capacity in the middle stage than to a downstream problem.",
            "root_back_flow_reason": "Pending secondary-sort stock is {stock} trays and today's finished/secondary ratio is only {ratio}%, which means post-kiln secondary sorting, finished push, or shipping handover deserves priority improvement.",
            "stage_front_reason": "Front-stage balance {front_balance} points, sawing stock {saw} trays, dipping stock {dip} trays, today's dip/saw ratio {ratio}%",
            "stage_middle_reason": "Middle-stage flow {middle_flow} points, kiln health {kiln_health} points, pending kiln stock {sorting} trays, active/ready kilns {active} units, suspected overdue {overdue} units",
            "stage_back_reason": "Backlog health {backlog_health} points, finished-goods health {product_health} points, pending secondary-sort {stock} trays, finished goods {product_count} pcs, today's finished/secondary ratio {ratio}%",
        }
    if lc == "my":
        return {
            "stage_front": "ရှေ့ပိုင်း (လွှဖြတ် / ဆေးစိမ်)",
            "stage_middle": "အလယ်ပိုင်း (ရွေးချယ် / မီးဖိုဝင် / မီးဖိုထွက်)",
            "stage_middle_load": "အလယ်ပိုင်း (ရွေးချယ် / မီးဖိုတင်နှုန်း)",
            "stage_back": "နောက်ပိုင်း (ဒုတိယရွေး / ကုန်ချော / ပို့ဆောင်မှု)",
            "stage_back_carry": "နောက်ပိုင်း (ဒုတိယရွေး / မီးဖိုထွက်လက်ခံ / ကုန်ချောတင်ဆက်မှု)",
            "weakest_default": "အလယ်ပိုင်း",
            "weakest_reason": "လက်ရှိစနစ်အကဲဖြတ်ချက်အရ ဒီအပိုင်းက အမှတ်အနည်းဆုံးဖြစ်နေသည်။",
            "symptom_label": "လက်ရှိဖိအားပေါ်နေသောအပိုင်း",
            "root_label": "ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်း",
            "root_bottleneck_reply": "သတ်မှတ်ချက်: အရင်တိုးမြှင့်သင့်သောအပိုင်းမှာ \"{root}\" ဖြစ်နိုင်ခြေများသည်။",
            "root_bottleneck_basis": "အကြောင်းပြချက်: {reason}",
            "symptom_reply": "ပေါ်ပင်လက္ခဏာ: အထင်ရှားဆုံးနှေးကွေးမှုက {symptom} မှာ မြင်ရသည်။",
            "second_reply": "နှိုင်းယှဉ်ချက်: ဒုတိယအနည်းဆုံးအပိုင်းက {name} ဖြစ်ပြီး အမှတ် {score} ဖြစ်သည်။",
            "advice_root_first": "အကြံပြုချက်: ပေါ်ပင်လက္ခဏာနောက်မလိုက်ဘဲ ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်းကို အရင်ဆွဲတင်ပါ။",
            "adjust_reply": "သတ်မှတ်ချက်: အခု အရင်ဆွဲတင်သင့်တဲ့အပိုင်းက \"{root}\" ဖြစ်သည်။",
            "adjust_basis": "အကြောင်းပြချက်: {reason}",
            "adjust_advice": "အကြံပြုချက်: ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်းရဲ့ rhythm ကို အရင်ပြန်ဆွဲတင်ပြီးနောက် ဖိအားပေါ်နေတဲ့အပိုင်း ပြန်တည်ငြိမ်မလား စောင့်ကြည့်ပါ။",
            "generic_title": "သတ်မှတ်ချက်: ပေါ်ပင်ပြသနာနောက်မလိုက်ဘဲ ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်းအလိုက် စီမံပါ။",
            "generic_basis": "အကြောင်းပြချက်:",
            "generic_top_score": "- စနစ်တစ်ခုလုံးအမှတ် {score}",
            "generic_bottleneck": "- လက်ရှိဖိအားပေါ်နေသောအပိုင်း {name}: {reason}",
            "generic_root": "- ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်း {name}: {reason}",
            "generic_second": "- ဒုတိယအနည်းဆုံးအပိုင်း {name}: {reason}",
            "generic_advice": "အကြံပြုချက်များ:\n1. ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်းကို အရင်ဆွဲတင်ပါ။\n2. ဖိအားပေါ်နေတဲ့အပိုင်း သဘာဝအတိုင်း တည်ငြိမ်လာမလား စောင့်ကြည့်ပါ။\n3. နောက်မှ upstream/downstream rhythm ကို ချိန်ညှိပါ။",
            "context_title": "လက်ရှိ လုပ်ငန်းဒေတာ:",
            "context_log_stock": "- ထင်းစတော့: {value} MT",
            "context_saw_stock": "- လွှဖြတ်စတော့: {value} ထပ်",
            "context_dip_stock": "- ဆေးစိမ်စတော့: {value} ထပ်",
            "context_sorting_stock": "- မီးဖိုဝင်ရန်စတော့: {value} ထပ်",
            "context_kiln_done_stock": "- ဒုတိယရွေးရန်စတော့: {value} ထပ်",
            "context_product_stock": "- ကုန်ချောစတော့: {count} ခု / {m3} m3",
            "context_ship_ygn": "- ရန်ကုန်သို့ လမ်းပေါ်: {value} စာရင်း",
            "context_ship_arrived": "- ရန်ကုန်ဂိုဒေါင်ရောက်: {value} စာရင်း",
            "context_ship_departed": "- ရန်ကုန်မှထွက်ပြီး: {value} စာရင်း",
            "context_system_summary": "- စနစ်တစ်ခုလုံး သုံးသပ်ချက်:",
            "context_total_score": "  - စုစုပေါင်းအမှတ်: {value}",
            "context_front_score": "  - ရှေ့ပိုင်းအမှတ်: {value}",
            "context_middle_score": "  - အလယ်ပိုင်းအမှတ်: {value}",
            "context_back_score": "  - နောက်ပိုင်းအမှတ်: {value}",
            "context_symptom_stage": "  - လက်ရှိဖိအားပေါ်နေသောအပိုင်း: {value}",
            "context_symptom_reason": "  - ဖိအားရှင်းလင်းချက်: {value}",
            "context_root_stage": "  - ဦးစားပေးတိုးမြှင့်ရမည့်အပိုင်း: {value}",
            "context_root_reason": "  - တိုးမြှင့်ရှင်းလင်းချက်: {value}",
            "context_ratio_dip_vs_saw": "  - ယနေ့ ဆေးစိမ်/လွှဖြတ် အချိုး: {value}%",
            "context_ratio_sort_vs_dip": "  - ယနေ့ ရွေးချယ်/ဆေးစိမ် အချိုး: {value}%",
            "context_ratio_secondary_vs_sort": "  - ယနေ့ ဒုတိယရွေး/ရွေးချယ် အချိုး: {value}%",
            "context_ratio_product_vs_secondary": "  - ယနေ့ ကုန်ချော/ဒုတိယရွေး အချိုး: {value}%",
            "context_kilns": "- မီးဖိုအခြေအနေ:",
            "overview_total": "စုစုပေါင်း {value}",
            "overview_front": "ရှေ့ပိုင်း {value}",
            "overview_middle": "အလယ်ပိုင်း {value}",
            "overview_back": "နောက်ပိုင်း {value}",
            "overview_kiln_abnormal": "မီးဖိုမူမမှန် {value} လုံး",
            "brief": "အရင်တိုးမြှင့်သင့်သောအပိုင်းမှာ \"{root}\" ဖြစ်နိုင်ခြေများပြီး၊ လက်ရှိဖိအားက \"{symptom}\" မှာ ပိုထင်ရှားနေသည်။",
            "recommendation_1": "ပေါ်ပင်လက္ခဏာကိုသာ မလိုက်ဘဲ \"{root}\" အပိုင်းကို အရင်ဆွဲတင်ပါ။",
            "recommendation_2": "လက္ခဏာက မီးဖိုဘက်မှာ မြင်နေရရင် မီးဖိုကို အရင်မစွပ်စွဲဘဲ မီးဖိုထွက်လက်ခံမှု၊ ဒုတိယရွေးနှင့် ကုန်ချောတင်ဆက်မှုကို စစ်ပါ။",
            "recommendation_3": "မီးဖိုအလွတ်များနေရင် လွှဖြတ် သို့မဟုတ် ဆေးစိမ် rhythm ကိုမပြောင်းခင် upstream supply နဲ့ မီးဖိုတင်ဆက်မှုကို အရင်လိုက်ကြည့်ပါ။",
            "root_back_reason": "လက္ခဏာက မီးဖိုဘက်မှာ တွေ့ရပေမယ့် အရင်းခံပြဿနာက မီးဖိုထွက်နောက်ပိုင်းမှာ ပိုဖြစ်နိုင်သည်။ Ready/unloading အချိန်ကျော် မီးဖို {overdue} လုံးရှိပြီး ဒုတိယရွေးရန်စတော့က {stock} ထပ်ပဲရှိသဖြင့် မီးဖိုအတွင်းနှေးခြင်းထက် မီးဖိုထွက်လက်ခံမှု၊ ဒုတိယရွေး သို့မဟုတ် ကုန်ချောတင်ဆက်မှု မကောင်းခြင်းကို ပိုညွှန်းနေသည်။",
            "root_front_reason": "အလွတ်မီးဖို {empty} လုံးရှိပြီး မီးဖိုဝင်ရန်စတော့ {sorting} ထပ်သာရှိသဖြင့် မီးဖိုရှေ့ feed မလုံလောက်နေသည်။ ဆေးစိမ်စတော့ {dip} ထပ်နှင့် ယနေ့ ဆေးစိမ်/လွှဖြတ် အချိုး {ratio}% ကိုကြည့်လျှင် ရှေ့ပိုင်း supply မလုံလောက်ခြင်းကို ပိုညွှန်းသည်။",
            "root_middle_reason": "အလွတ်မီးဖို {empty} လုံးရှိပေမယ့် လွှဖြတ်စတော့ {saw} ထပ်က မနည်းသေးသဖြင့် စုစုပေါင်း feed မရှိတာမဟုတ်ပါ။ ဆေးစိမ်ပြီးကနေ ရွေးချယ်၊ မီးဖိုတင်ဆက်မှုကြား ဟန်ချက်မညီတာဖြစ်နိုင်ပြီး မီးဖိုဝင်ရန်စတော့က {sorting} ထပ်ပဲရှိသည်။",
            "root_middle_load_reason": "မီးဖိုဝင်ရန်စတော့ {sorting} ထပ်အထိတက်လာတာက ရှေ့ပိုင်းက material ကို တွန်းပို့ထားပြီးဖြစ်ကြောင်း ပြသသော်လည်း မီးဖိုတင်နှုန်းက မလိုက်နိုင်သေးပါ။ ဒါက နောက်ပိုင်းထက် အလယ်ပိုင်း digest capacity အားနည်းခြင်းကို ပိုညွှန်းသည်။",
            "root_back_flow_reason": "ဒုတိယရွေးရန်စတော့ {stock} ထပ်ရှိပြီး ယနေ့ ကုန်ချော/ဒုတိယရွေး အချိုးက {ratio}% ပဲရှိသဖြင့် မီးဖိုထွက်ပြီးနောက် ဒုတိယရွေး၊ ကုန်ချောတင်ဆက်မှု သို့မဟုတ် ပို့ဆောင်ရေးလက်ခံမှုကို အရင်တိုးမြှင့်သင့်ကြောင်း ပိုညွှန်းနေသည်။",
            "stage_front_reason": "ရှေ့ပိုင်းဟန်ချက် {front_balance} မှတ်၊ လွှဖြတ်စတော့ {saw} ထပ်၊ ဆေးစိမ်စတော့ {dip} ထပ်၊ ယနေ့ ဆေးစိမ်/လွှဖြတ် အချိုး {ratio}%",
            "stage_middle_reason": "အလယ်ပိုင်း flow {middle_flow} မှတ်၊ မီးဖိုကျန်းမာရေး {kiln_health} မှတ်၊ မီးဖိုဝင်ရန်စတော့ {sorting} ထပ်၊ လည်ပတ်/စောင့်မီးဖို {active} လုံး၊ အချိန်ကျော်သံသယ {overdue} လုံး",
            "stage_back_reason": "တန်းစီကျန်းမာရေး {backlog_health} မှတ်၊ ကုန်ချောကျန်းမာရေး {product_health} မှတ်၊ ဒုတိယရွေးရန်စတော့ {stock} ထပ်၊ ကုန်ချော {product_count} ခု၊ ယနေ့ ကုန်ချော/ဒုတိယရွေး အချိုး {ratio}%",
        }
    return {
        "stage_front": "前段（锯解/药浸）",
        "stage_middle": "中段（拣选/入窑/出窑）",
        "stage_middle_load": "中段（拣选/入窑/装窑节拍）",
        "stage_back": "后段（二选/成品/发货）",
        "stage_back_carry": "后段（二选/出窑承接/成品推进）",
        "weakest_default": "中段",
        "weakest_reason": "当前系统判断该环节评分最低。",
        "symptom_label": "当前压力位置",
        "root_label": "优先提升环节",
        "root_bottleneck_reply": "结论：当前最该优先提升的环节更像在「{root}」。",
        "root_bottleneck_basis": "依据：{reason}",
        "symptom_reply": "当前压力位置：当前最明显的卡顿表现出现在 {symptom}。",
        "second_reply": "对比：第二弱的是 {name}，评分 {score}。",
        "advice_root_first": "建议：先把优先提升环节拉起来，再看压力位置是否会随之缓解。",
        "adjust_reply": "结论：现在应该先把「{root}」这一段提起来。",
        "adjust_basis": "依据：{reason}",
        "adjust_advice": "建议：先把优先提升环节拉回到日常节拍，再同步看压力位置是否自然缓解。",
        "generic_title": "结论：先按优先提升环节来处理，不要只跟着表面症状走。",
        "generic_basis": "依据：",
        "generic_top_score": "- 全流程总分 {score}",
        "generic_bottleneck": "- 当前压力位置 {name}: {reason}",
        "generic_root": "- 优先提升环节 {name}: {reason}",
        "generic_second": "- 第二弱环节 {name}: {reason}",
        "generic_advice": "建议：\n1. 先把优先提升环节拉起来。\n2. 再观察压力位置是否自然回稳。\n3. 最后再调整上下游节拍。",
        "context_title": "实时经营数据：",
        "context_log_stock": "- 原木库存: {value} MT",
        "context_saw_stock": "- 锯解库存: {value} 托",
        "context_dip_stock": "- 药浸库存: {value} 托",
        "context_sorting_stock": "- 待入窑库存: {value} 托",
        "context_kiln_done_stock": "- 待二选库存: {value} 托",
        "context_product_stock": "- 成品库存: {count} 件 / {m3} m3",
        "context_ship_ygn": "- 发货途中: {value} 单",
        "context_ship_arrived": "- 仰光仓已到: {value} 单",
        "context_ship_departed": "- 已从仰光出港: {value} 单",
        "context_system_summary": "- 系统全盘判断摘要:",
        "context_total_score": "  - 全流程总分: {value}",
        "context_front_score": "  - 前段评分: {value}",
        "context_middle_score": "  - 中段评分: {value}",
        "context_back_score": "  - 后段评分: {value}",
        "context_symptom_stage": "  - 当前压力位置: {value}",
        "context_symptom_reason": "  - 压力说明: {value}",
        "context_root_stage": "  - 优先提升环节: {value}",
        "context_root_reason": "  - 提升依据: {value}",
        "context_ratio_dip_vs_saw": "  - 今日药浸/锯解转化比: {value}%",
        "context_ratio_sort_vs_dip": "  - 今日拣选/药浸转化比: {value}%",
        "context_ratio_secondary_vs_sort": "  - 今日二选/拣选转化比: {value}%",
        "context_ratio_product_vs_secondary": "  - 今日成品/二选转化比: {value}%",
        "context_kilns": "- 窑状态:",
        "overview_total": "总分 {value}",
        "overview_front": "前段 {value}",
        "overview_middle": "中段 {value}",
        "overview_back": "后段 {value}",
        "overview_kiln_abnormal": "窑状态异常 {value} 台",
        "brief": "当前最该优先提升的环节更像在「{root}」，现场压力主要出现在「{symptom}」。",
        "recommendation_1": "先把「{root}」这一段提起来，不要只追着表面症状处理。",
        "recommendation_2": "如果症状在窑端，优先检查出窑承接、二选排产和成品推进，而不是先怀疑窑本体。",
        "recommendation_3": "如果空窑偏多，先追前段供料与入窑衔接，再决定是否调整锯解或药浸节奏。",
        "root_back_reason": "症状出现在窑端，但根本原因更像在窑后承接。完成待出/出窑超时 {overdue} 台，而待二选只有 {stock} 托，说明不是窑内继续加工慢，而是出窑后的承接、二选或成品推进不顺。",
        "root_front_reason": "空窑 {empty} 台且待入窑只有 {sorting} 托，说明窑前缺料。同时药浸库存 {dip} 托、今日药浸/锯解转化比 {ratio}%，更像前段供料不足。",
        "root_middle_reason": "空窑 {empty} 台，但锯解库存 {saw} 托不算低，说明不是完全没料，更像药浸后到拣选、入窑这段衔接不足，待入窑只有 {sorting} 托。",
        "root_middle_load_reason": "待入窑 {sorting} 托偏高，说明前段已把料推上来，但装窑/入窑节拍没有跟上。这更像中段消化能力不足，而不是后段问题。",
        "root_back_flow_reason": "待二选 {stock} 托且今日成品/二选转化比只有 {ratio}%，说明出窑后的二选、成品推进或发货承接更该优先提升。",
        "stage_front_reason": "前段均衡 {front_balance} 分，锯解库存 {saw} 托，药浸库存 {dip} 托，今日药浸/锯解转化比 {ratio}%",
        "stage_middle_reason": "中段流速 {middle_flow} 分，窑效率 {kiln_health} 分，待入窑 {sorting} 托，运行中/待出的窑 {active} 台，其中疑似超时 {overdue} 台",
        "stage_back_reason": "积压健康 {backlog_health} 分，成品健康 {product_health} 分，待二选 {stock} 托，成品 {product_count} 件，今日成品/二选转化比 {ratio}%",
    }


def _round1(value):
    try:
        return round(float(value), 1)
    except Exception:
        return 0.0


def _stage_triplet(vec: dict) -> dict[str, float]:
    cur = vec if isinstance(vec, dict) else {}
    return {
        "front": _round1((float(cur.get("raw_security", 0)) + float(cur.get("front_balance", 0))) / 2.0),
        "middle": _round1((float(cur.get("middle_flow", 0)) + float(cur.get("kiln_health", 0))) / 2.0),
        "back": _round1((float(cur.get("backlog_health", 0)) + float(cur.get("product_health", 0))) / 2.0),
    }


def _build_weekly_progress(efficiency: dict, throughput: dict, stages_by_key: dict[str, dict], lang: str = "zh") -> dict:
    lc = str(lang or "zh").strip().lower()
    week_scores = _stage_triplet((efficiency or {}).get("week", {}))
    week_prev_scores = _stage_triplet((efficiency or {}).get("week_prev", {}))
    product_week = (((throughput or {}).get("comparison") or {}).get("week") or {}) if isinstance(throughput, dict) else {}
    product_m3 = _round1(product_week.get("product_m3", 0))
    product_mom = product_week.get("mom_pct")
    try:
        product_mom = round(float(product_mom), 1)
    except Exception:
        product_mom = None

    rows = []
    for key in ("front", "middle", "back"):
        current = week_scores.get(key, 0.0)
        prev = week_prev_scores.get(key, 0.0)
        delta = _round1(current - prev)
        stage = stages_by_key.get(key, {}) if isinstance(stages_by_key, dict) else {}
        rows.append(
            {
                "key": key,
                "name": str(stage.get("name") or key),
                "score": current,
                "prev_score": prev,
                "delta": delta,
                "reason": str(stage.get("reason") or ""),
            }
        )
    rows.sort(key=lambda item: (float(item.get("delta", 0)), float(item.get("score", 0))))
    lag_stage = rows[0] if rows else {"name": "-", "delta": 0.0, "reason": ""}
    lead_stage = rows[-1] if rows else {"name": "-", "delta": 0.0, "reason": ""}
    stagnant = [row for row in rows if float(row.get("delta", 0)) <= 0.5]

    if lc == "en":
        if stagnant:
            summary = f"This week the weakest improvement is in {lag_stage['name']} ({lag_stage['delta']:+.1f}), so it should be the next productivity push."
        else:
            summary = f"All three major stages improved this week; {lead_stage['name']} is pulling the strongest ({lead_stage['delta']:+.1f})."
        actions = [
            f"First review why {lag_stage['name']} did not improve enough this week.",
            f"Then keep the best practice from {lead_stage['name']} and copy it where possible.",
            f"Weekly finished output is {product_m3:.1f} m3" + (f", WoW {product_mom:+.1f}%." if product_mom is not None else "."),
        ]
    elif lc == "my":
        if stagnant:
            summary = f"ဒီအပတ်မှာ တိုးတက်မှုအနည်းဆုံးအပိုင်းက {lag_stage['name']} ({lag_stage['delta']:+.1f}) ဖြစ်ပြီး နောက်တစ်ဆင့် productivity push ကို အဲဒီမှာထားသင့်ပါသည်။"
        else:
            summary = f"ဒီအပတ် အဓိကအပိုင်း ၃ ခုလုံး တိုးတက်လာပြီး {lead_stage['name']} က အကောင်းဆုံးဆွဲတင်နေပါသည် ({lead_stage['delta']:+.1f})။"
        actions = [
            f"{lag_stage['name']} ဘာကြောင့် ဒီအပတ်မတိုးတက်သလဲကို အရင်ပြန်စစ်ပါ။",
            f"{lead_stage['name']} မှာရတဲ့ practice ကောင်းကို အခြားအပိုင်းများသို့ ပြန်ကူးပါ။",
            f"ဒီအပတ်ကုန်ချောထွက်အား {product_m3:.1f} m3" + (f", WoW {product_mom:+.1f}%." if product_mom is not None else "."),
        ]
    else:
        if stagnant:
            summary = f"本周提升最慢的是「{lag_stage['name']}」({lag_stage['delta']:+.1f})，下一步要优先盯它为什么没提上来。"
        else:
            summary = f"本周三大环节都有提升，其中「{lead_stage['name']}」拉升最明显（{lead_stage['delta']:+.1f}）。"
        actions = [
            f"先复盘「{lag_stage['name']}」为什么本周没有明显提升。",
            f"把「{lead_stage['name']}」的有效做法复制到其他环节。",
            f"本周成品产出 {product_m3:.1f} m3" + (f"，环比 {product_mom:+.1f}% 。" if product_mom is not None else "。"),
        ]

    return {
        "summary": summary,
        "lag_stage": lag_stage,
        "lead_stage": lead_stage,
        "rows": rows,
        "actions": actions[:3],
        "product_week_m3": product_m3,
        "product_week_mom_pct": product_mom,
    }


def summarize_kilns(stock_data: dict) -> dict:
    kiln_status = stock_data.get("kiln_status", {}) if isinstance(stock_data, dict) else {}
    summary = {
        "empty": 0,
        "drying": 0,
        "ready": 0,
        "unloading": 0,
        "active_load": 0,
        "overdue_like": 0,
        "ready_overdue": 0,
        "unloading_overdue": 0,
        "drying_overdue": 0,
    }
    for kiln_id in ("A", "B", "C", "D"):
        info = kiln_status.get(kiln_id, {}) if isinstance(kiln_status, dict) else {}
        status = str(info.get("status") or "").strip().lower()
        duration = float(info.get("status_duration_hours") or 0.0)
        if status in summary:
            summary[status] += 1
        if status in ("drying", "ready", "unloading"):
            summary["active_load"] += 1
        if status == "ready" and duration >= 24:
            summary["ready_overdue"] += 1
            summary["overdue_like"] += 1
        elif status == "unloading" and duration >= 24:
            summary["unloading_overdue"] += 1
            summary["overdue_like"] += 1
        elif status == "drying" and duration >= 120:
            summary["drying_overdue"] += 1
            summary["overdue_like"] += 1
    return summary


def _infer_root_bottleneck(stock_data: dict, day_tp: dict, kiln_summary: dict, stages: list[dict], lang: str = "zh") -> dict:
    lp = _lang_pack(lang)
    sorting_stock = int(stock_data.get("sorting_stock", 0) or 0)
    kiln_done_stock = int(stock_data.get("kiln_done_stock", 0) or 0)
    saw_stock = int(stock_data.get("saw_stock", 0) or 0)
    dip_stock = int(stock_data.get("dip_stock", 0) or 0)

    ratio_dip_vs_saw = float(day_tp.get("ratio_dip_vs_saw", 0) or 0)
    ratio_product_vs_secondary = float(day_tp.get("ratio_product_vs_secondary", 0) or 0)

    ready_overdue = int(kiln_summary.get("ready_overdue", 0) or 0)
    unloading_overdue = int(kiln_summary.get("unloading_overdue", 0) or 0)
    empty_kilns = int(kiln_summary.get("empty", 0) or 0)

    weakest = stages[0] if stages else {"key": "middle", "name": lp["weakest_default"], "reason": lp["weakest_reason"]}
    middle_stage = next((s for s in stages if s.get("key") == "middle"), weakest)

    if (ready_overdue + unloading_overdue) >= 2 and kiln_done_stock <= max(8, int(day_tp.get("secondary_trays", 0) or 0)):
        return {
            "key": "back",
            "name": lp["stage_back_carry"],
            "reason": lp["root_back_reason"].format(overdue=ready_overdue + unloading_overdue, stock=kiln_done_stock),
            "symptom_stage": middle_stage.get("name", lp["weakest_default"]),
        }

    if empty_kilns >= 2 and sorting_stock <= 6:
        if dip_stock <= 2 and ratio_dip_vs_saw < 75:
            return {
                "key": "front",
                "name": lp["stage_front"],
                "reason": lp["root_front_reason"].format(empty=empty_kilns, sorting=sorting_stock, dip=dip_stock, ratio=ratio_dip_vs_saw),
                "symptom_stage": middle_stage.get("name", lp["weakest_default"]),
            }
        return {
            "key": "middle",
            "name": lp["stage_middle"],
            "reason": lp["root_middle_reason"].format(empty=empty_kilns, saw=saw_stock, sorting=sorting_stock),
            "symptom_stage": middle_stage.get("name", lp["weakest_default"]),
        }

    if sorting_stock >= max(12, int(day_tp.get("sort_trays", 0) or 0)):
        return {
            "key": "middle",
            "name": lp["stage_middle_load"],
            "reason": lp["root_middle_load_reason"].format(sorting=sorting_stock),
            "symptom_stage": middle_stage.get("name", lp["weakest_default"]),
        }

    if kiln_done_stock >= max(10, int(day_tp.get("secondary_trays", 0) or 0)) and ratio_product_vs_secondary < 92:
        return {
            "key": "back",
            "name": lp["stage_back"],
            "reason": lp["root_back_flow_reason"].format(stock=kiln_done_stock, ratio=ratio_product_vs_secondary),
            "symptom_stage": lp["stage_back"],
        }

    return {
        "key": weakest.get("key", "middle"),
        "name": weakest.get("name", lp["weakest_default"]),
        "reason": weakest.get("reason", lp["weakest_reason"]),
        "symptom_stage": weakest.get("name", lp["weakest_default"]),
    }


def build_factory_intelligence(stock_data: dict, efficiency: dict, throughput: dict, lang: str = "zh") -> dict:
    lp = _lang_pack(lang)
    current = efficiency.get("current", {}) if isinstance(efficiency, dict) else {}
    day = efficiency.get("day", {}) if isinstance(efficiency, dict) else {}
    day_tp = throughput.get("current_day", {}) if isinstance(throughput, dict) else {}

    kiln_summary = summarize_kilns(stock_data)
    sorting_stock = int(stock_data.get("sorting_stock", 0) or 0)
    kiln_done_stock = int(stock_data.get("kiln_done_stock", 0) or 0)
    saw_stock = int(stock_data.get("saw_stock", 0) or 0)
    dip_stock = int(stock_data.get("dip_stock", 0) or 0)
    product_count = int(stock_data.get("product_count", 0) or 0)

    front_score = _round1((float(current.get("raw_security", 0)) + float(current.get("front_balance", 0))) / 2.0)
    middle_score = _round1((float(current.get("middle_flow", 0)) + float(current.get("kiln_health", 0))) / 2.0)
    back_score = _round1((float(current.get("backlog_health", 0)) + float(current.get("product_health", 0))) / 2.0)

    day_front = _round1((float(day.get("raw_security", 0)) + float(day.get("front_balance", 0))) / 2.0)
    day_middle = _round1((float(day.get("middle_flow", 0)) + float(day.get("kiln_health", 0))) / 2.0)
    day_back = _round1((float(day.get("backlog_health", 0)) + float(day.get("product_health", 0))) / 2.0)

    stages = [
        {
            "key": "front",
            "name": lp["stage_front"],
            "score": front_score,
            "day_score": day_front,
            "reason": lp["stage_front_reason"].format(
                front_balance=current.get("front_balance", 0),
                saw=saw_stock,
                dip=dip_stock,
                ratio=day_tp.get("ratio_dip_vs_saw", 0),
            ),
        },
        {
            "key": "middle",
            "name": lp["stage_middle"],
            "score": middle_score,
            "day_score": day_middle,
            "reason": lp["stage_middle_reason"].format(
                middle_flow=current.get("middle_flow", 0),
                kiln_health=current.get("kiln_health", 0),
                sorting=sorting_stock,
                active=kiln_summary.get("active_load", 0),
                overdue=kiln_summary.get("overdue_like", 0),
            ),
        },
        {
            "key": "back",
            "name": lp["stage_back"],
            "score": back_score,
            "day_score": day_back,
            "reason": lp["stage_back_reason"].format(
                backlog_health=current.get("backlog_health", 0),
                product_health=current.get("product_health", 0),
                stock=kiln_done_stock,
                product_count=product_count,
                ratio=day_tp.get("ratio_product_vs_secondary", 0),
            ),
        },
    ]
    stages.sort(key=lambda item: (float(item.get("score", 0)), float(item.get("day_score", 0))))
    stages_by_key = {str(item.get("key") or ""): item for item in stages}
    bottleneck = stages[0] if stages else {"name": lp["weakest_default"], "score": 0, "reason": ""}
    root_bottleneck = _infer_root_bottleneck(stock_data, day_tp, kiln_summary, stages, lang=lang)
    weekly_progress = _build_weekly_progress(efficiency, throughput, stages_by_key, lang=lang)

    recommendations = [
        lp["recommendation_1"].format(root=root_bottleneck.get("name", bottleneck.get("name", "-"))),
        lp["recommendation_2"],
        lp["recommendation_3"],
    ]

    overview_parts = [
        lp["overview_total"].format(value=current.get("total_score", 0)),
        lp["overview_front"].format(value=front_score),
        lp["overview_middle"].format(value=middle_score),
        lp["overview_back"].format(value=back_score),
    ]
    if kiln_summary.get("overdue_like", 0) > 0:
        overview_parts.append(lp["overview_kiln_abnormal"].format(value=kiln_summary.get("overdue_like", 0)))

    separator = "；" if str(lang or "zh").strip().lower() == "zh" else " | "

    return {
        "stage_scores": stages,
        "bottleneck": bottleneck,
        "root_bottleneck": root_bottleneck,
        "priority_stage": {
            "name": root_bottleneck.get("name", bottleneck.get("name", "-")),
            "reason": root_bottleneck.get("reason", bottleneck.get("reason", "")),
        },
        "pressure_stage": {
            "name": bottleneck.get("name", "-"),
            "reason": bottleneck.get("reason", ""),
        },
        "kiln_summary": kiln_summary,
        "overview": separator.join(overview_parts),
        "brief": lp["brief"].format(
            root=root_bottleneck.get("name", bottleneck.get("name", "-")),
            symptom=root_bottleneck.get("symptom_stage", bottleneck.get("name", "-")),
        ),
        "recommendations": recommendations,
        "weekly_progress": weekly_progress,
    }


def build_factory_context(stock_data: dict, analysis: dict, efficiency: dict, throughput: dict, lang: str = "zh") -> str:
    lp = _lang_pack(lang)
    kiln_lines = []
    kiln_status = stock_data.get("kiln_status", {}) if isinstance(stock_data, dict) else {}
    for kiln_id in ["A", "B", "C", "D"]:
        info = kiln_status.get(kiln_id, {}) if isinstance(kiln_status, dict) else {}
        status_label = str(info.get("status_display") or info.get("status") or "-").strip()
        progress = str(info.get("progress") or "").strip()
        tail = f" | {progress}" if progress else ""
        kiln_lines.append(f"{kiln_id}窑: {status_label}{tail}")

    current = efficiency.get("current", {}) if isinstance(efficiency, dict) else {}
    day_tp = throughput.get("current_day", {}) if isinstance(throughput, dict) else {}
    stage_scores = list((analysis or {}).get("stage_scores") or [])
    bottleneck = (analysis or {}).get("bottleneck", {}) if isinstance(analysis, dict) else {}
    root_bottleneck = (analysis or {}).get("root_bottleneck", {}) if isinstance(analysis, dict) else {}
    shipping_summary = stock_data.get("shipping_summary", {}) if isinstance(stock_data, dict) else {}

    return "\n".join(
        [
            lp["context_title"],
            lp["context_log_stock"].format(value=stock_data.get("log_stock", 0)),
            lp["context_saw_stock"].format(value=stock_data.get("saw_stock", 0)),
            lp["context_dip_stock"].format(value=stock_data.get("dip_stock", 0)),
            lp["context_sorting_stock"].format(value=stock_data.get("sorting_stock", 0)),
            lp["context_kiln_done_stock"].format(value=stock_data.get("kiln_done_stock", 0)),
            lp["context_product_stock"].format(count=stock_data.get("product_count", 0), m3=stock_data.get("product_m3", 0)),
            lp["context_ship_ygn"].format(value=shipping_summary.get("去仰光途中", 0)),
            lp["context_ship_arrived"].format(value=shipping_summary.get("仰光仓已到", 0)),
            lp["context_ship_departed"].format(value=shipping_summary.get("已从仰光出港", 0)),
            lp["context_system_summary"],
            lp["context_total_score"].format(value=current.get("total_score", 0)),
            lp["context_front_score"].format(value=next((s.get("score") for s in stage_scores if s.get("key") == "front"), 0)),
            lp["context_middle_score"].format(value=next((s.get("score") for s in stage_scores if s.get("key") == "middle"), 0)),
            lp["context_back_score"].format(value=next((s.get("score") for s in stage_scores if s.get("key") == "back"), 0)),
            lp["context_symptom_stage"].format(value=bottleneck.get("name", "-")),
            lp["context_symptom_reason"].format(value=bottleneck.get("reason", "-")),
            lp["context_root_stage"].format(value=root_bottleneck.get("name", bottleneck.get("name", "-"))),
            lp["context_root_reason"].format(value=root_bottleneck.get("reason", bottleneck.get("reason", "-"))),
            lp["context_ratio_dip_vs_saw"].format(value=day_tp.get("ratio_dip_vs_saw", 0)),
            lp["context_ratio_sort_vs_dip"].format(value=day_tp.get("ratio_sort_vs_dip", 0)),
            lp["context_ratio_secondary_vs_sort"].format(value=day_tp.get("ratio_secondary_vs_sort", 0)),
            lp["context_ratio_product_vs_secondary"].format(value=day_tp.get("ratio_product_vs_secondary", 0)),
            lp["context_kilns"],
            *[f"  - {line}" for line in kiln_lines],
        ]
    )


def build_factory_fallback_answer(question: str, analysis: dict, total_score: float, lang: str = "zh") -> str:
    lp = _lang_pack(lang)
    bottleneck = analysis.get("bottleneck", {}) if isinstance(analysis, dict) else {}
    root_bottleneck = analysis.get("root_bottleneck", {}) if isinstance(analysis, dict) else {}
    stage_scores = list((analysis or {}).get("stage_scores") or [])
    q = str(question or "").strip()

    if any(token in q.lower() for token in ("bottleneck", "stuck", "slowest")) or any(token in q for token in ("瓶颈", "卡在哪", "卡在", "堵点", "最慢")):
        second = stage_scores[1] if len(stage_scores) > 1 else {}
        return (
            lp["root_bottleneck_reply"].format(root=root_bottleneck.get("name", bottleneck.get("name", lp["weakest_default"])))
            + "\n"
            + lp["root_bottleneck_basis"].format(reason=root_bottleneck.get("reason", bottleneck.get("reason", lp["weakest_reason"])))
            + (f"\n{lp['symptom_reply'].format(symptom=root_bottleneck.get('symptom_stage', bottleneck.get('name', lp['weakest_default'])))}" if root_bottleneck else "")
            + (f"\n{lp['second_reply'].format(name=second.get('name'), score=second.get('score'))}" if second else "")
            + "\n"
            + lp["advice_root_first"]
        )

    if any(token in q.lower() for token in ("backlog", "adjust first", "which stage first", "what should we adjust first")) or any(token in q for token in ("积压", "调哪一段", "先调哪一段", "先调哪里")):
        return (
            lp["adjust_reply"].format(root=root_bottleneck.get("name", bottleneck.get("name", lp["weakest_default"])))
            + "\n"
            + lp["adjust_basis"].format(reason=root_bottleneck.get("reason", bottleneck.get("reason", lp["weakest_reason"])))
            + "\n"
            + lp["adjust_advice"]
        )

    top_lines = [
        lp["generic_top_score"].format(score=total_score),
        lp["generic_bottleneck"].format(name=bottleneck.get("name", "-"), reason=bottleneck.get("reason", "-")),
        lp["generic_root"].format(name=root_bottleneck.get("name", "-"), reason=root_bottleneck.get("reason", "-")),
    ]
    if len(stage_scores) > 1:
        top_lines.append(lp["generic_second"].format(name=stage_scores[1].get("name", "-"), reason=stage_scores[1].get("reason", "-")))
    return (
        lp["generic_title"]
        + "\n"
        + lp["generic_basis"]
        + "\n"
        + "\n".join(top_lines)
        + "\n"
        + lp["generic_advice"]
    )
