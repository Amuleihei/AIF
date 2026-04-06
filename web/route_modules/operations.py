# 页面与管理操作路由（从 routes.py 拆分）
import json

from web.route_support import (
    BARK_PRICE_PER_M3_KS,
    HTML_TEMPLATE,
    LANGUAGES,
    current_user,
    datetime,
    dispatch,
    get_lang,
    get_stock_data_with_lang,
    get_system_health_snapshot,
    login_required,
    jsonify,
    redirect,
    render_template_string,
    request,
    time,
    url_for,
    _load_kilns_data,
    _read_flow_data,
    _save_flow_data,
    _save_kilns_data,
    _set_raw_log_stock,
    audit_admin_action,
    _t,
    _to_float,
    _to_int,
)
from web.templates_boss import BOSS_H5_TEMPLATE
from web.services.entry_reminder_service import get_daily_missing_entry_status
from web.services.alert_center_service import get_alert_center_payload
from web.services.factory_intelligence_service import (
    build_factory_context as _shared_build_factory_context,
    build_factory_fallback_answer as _shared_build_factory_fallback_answer,
    build_factory_intelligence as _shared_build_factory_intelligence,
)
from modules.ai.ai_engine import ask_ai


def register_operations_routes(app, logger):
    def _round1(value):
        try:
            return round(float(value), 1)
        except Exception:
            return 0.0

    def _is_smalltalk_question(question: str) -> bool:
        text = str(question or "").strip().lower()
        if not text:
            return False
        smalltalk_tokens = (
            "你好",
            "早",
            "早啊",
            "早安",
            "晚安",
            "hello",
            "hi",
            "hey",
            "在吗",
            "在不在",
            "你是谁",
            "你叫什么",
            "介绍一下你自己",
            "谢谢",
            "辛苦了",
        )
        return any(token in text for token in smalltalk_tokens)

    def _needs_factory_context(question: str) -> bool:
        text = str(question or "").strip().lower()
        if not text:
            return False
        keywords = (
            "库存",
            "预警",
            "窑",
            "成品",
            "原木",
            "锯解",
            "药浸",
            "拣选",
            "二选",
            "发货",
            "排班",
            "堵",
            "积压",
            "瓶颈",
            "堵点",
            "调哪一段",
            "先调哪一段",
            "先调哪里",
            "整体情况",
            "产量",
            "效率",
            "生产",
            "工厂",
            "老板",
            "report",
            "inventory",
            "alert",
            "kiln",
            "shipment",
            "production",
        )
        return any(token in text for token in keywords)

    def _is_bottleneck_question(question: str) -> bool:
        text = str(question or "").strip().lower()
        if not text:
            return False
        keywords = (
            "瓶颈",
            "卡在哪",
            "卡在",
            "堵点",
            "哪环节最慢",
            "哪个环节最慢",
            "哪个环节拖后腿",
            "生产问题在哪",
            "生产瓶颈",
            "bottleneck",
        )
        return any(token in text for token in keywords)

    def _answer_uses_factory_context(answer: str) -> bool:
        text = str(answer or "").strip().lower()
        if not text:
            return False
        signals = (
            "原木",
            "锯解",
            "药浸",
            "待入窑",
            "待二选",
            "成品",
            "发货",
            "预警",
            "a窑",
            "b窑",
            "c窑",
            "d窑",
            "mt",
            "m3",
            "件",
            "托",
        )
        has_signal = any(token in text for token in signals)
        has_digit = any(ch.isdigit() for ch in text)
        return has_signal or has_digit

    def _is_generic_ai_answer(answer: str) -> bool:
        text = str(answer or "").strip().lower()
        if not text:
            return True
        generic_patterns = (
            "取决于你当前的情况",
            "取决于情况",
            "可以先看看",
            "如果具体信息不够",
            "可能需要根据",
            "视情况而定",
        )
        return any(token in text for token in generic_patterns)

    def _compose_ai_factory_answer(parsed: dict, analysis: dict) -> str:
        data = parsed if isinstance(parsed, dict) else {}
        direct = str(data.get("direct_answer") or "").strip()
        symptom = str(data.get("symptom_stage") or "").strip()
        root = str(data.get("root_stage") or "").strip()
        reason = str(data.get("reason") or "").strip()
        evidence = [str(x or "").strip() for x in (data.get("evidence") or []) if str(x or "").strip()]
        actions = [str(x or "").strip() for x in (data.get("actions") or []) if str(x or "").strip()]

        bottleneck = analysis.get("bottleneck", {}) if isinstance(analysis, dict) else {}
        root_bottleneck = analysis.get("root_bottleneck", {}) if isinstance(analysis, dict) else {}

        direct = direct or f"当前更该先把「{root or root_bottleneck.get('name', '-') }」这一段提起来。"
        symptom = symptom or str(bottleneck.get("name") or "-").strip()
        root = root or str(root_bottleneck.get("name") or symptom or "-").strip()
        reason = reason or str(root_bottleneck.get("reason") or bottleneck.get("reason") or "").strip()

        lines = [f"结论：{direct}"]
        if symptom:
            lines.append(f"当前压力位置：{symptom}")
        if root:
            lines.append(f"优先提升环节：{root}")
        if reason:
            lines.append(f"提升依据：{reason}")
        if evidence:
            lines.append("依据：")
            lines.extend(f"- {item}" for item in evidence[:4])
        if actions:
            lines.append("建议：")
            lines.extend(f"{idx}. {item}" for idx, item in enumerate(actions[:3], start=1))
        return "\n".join(lines)

    def _extract_json_block(raw_text: str) -> dict:
        text = str(raw_text or "").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except Exception:
            pass
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
        return {}

    def _structured_ai_factory_answer(question: str, stock_data: dict, lang: str, analysis: dict) -> str:
        context_text = _build_web_ai_context(stock_data, analysis)
        stage_names = [str(item.get("name") or "").strip() for item in (analysis.get("stage_scores") or []) if str(item.get("name") or "").strip()]
        root_guess = str(((analysis.get("root_bottleneck") or {}).get("name")) or "").strip()
        symptom_guess = str(((analysis.get("bottleneck") or {}).get("name")) or "").strip()
        prompt = (
            "下面是 AIF 系统的实时工厂数据。你不是来复读预警，也不是只挑一条数字说事。"
            "你必须自己综合整条链路，判断“当前压力主要出在哪”和“当前最该优先提升的环节更像在哪”。\n\n"
            f"{context_text}\n\n"
            f"用户问题：{question}\n\n"
            "请只输出 JSON，不要输出解释文字、不要加代码块。格式必须是：\n"
            "{"
            "\"direct_answer\":\"一句直接结论\","
            "\"symptom_stage\":\"当前压力位置\","
            "\"root_stage\":\"优先提升环节\","
            "\"reason\":\"一句提升依据\","
            "\"evidence\":[\"证据1\",\"证据2\",\"证据3\"],"
            "\"actions\":[\"建议1\",\"建议2\",\"建议3\"]"
            "}\n\n"
            "要求：\n"
            "1. direct_answer 必须正面回答用户问题，不要空话。\n"
            "2. symptom_stage 和 root_stage 不能写“未知”或“视情况而定”。\n"
            "3. evidence 必须引用实时数据里的真实数字、库存、转化比、窑状态或评分，至少 2 条。\n"
            "4. 不要把“预警标题”当结论。\n"
            "5. 如果压力表现在窑端，也要继续判断最该优先提升的环节是否其实在前后段。\n"
            f"6. 可参考的阶段名称：{', '.join(stage_names)}。\n"
            f"7. 系统当前的初步参考是：当前压力位置偏向「{symptom_guess}」，优先提升环节偏向「{root_guess}」。你可以同意，也可以推翻，但必须拿证据说话。"
        )
        system_prompt = (
            "你是 AIF 的厂务分析 AI。"
            "你的任务是用实时数据做跨环节推理，而不是套模板。"
            "你可以不同意系统初步判断，但必须引用事实。"
            "输出必须是合法 JSON。"
        )
        raw = ask_ai(prompt, system_prompt=system_prompt, max_tokens=520)
        parsed = _extract_json_block(raw)
        if not parsed:
            raise ValueError("AI 未返回有效 JSON")

        answer = _compose_ai_factory_answer(parsed, analysis)
        if not _answer_uses_factory_context(answer) or _is_generic_ai_answer(answer):
            raise ValueError("AI 返回内容未有效使用实时数据")
        return answer

    def _kiln_operating_summary(stock_data: dict) -> dict:
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

    def _infer_root_bottleneck(stock_data: dict, current: dict, day_tp: dict, kiln_summary: dict, stages: list[dict]) -> dict:
        sorting_stock = int(stock_data.get("sorting_stock", 0) or 0)
        kiln_done_stock = int(stock_data.get("kiln_done_stock", 0) or 0)
        saw_stock = int(stock_data.get("saw_stock", 0) or 0)
        dip_stock = int(stock_data.get("dip_stock", 0) or 0)

        ratio_dip_vs_saw = float(day_tp.get("ratio_dip_vs_saw", 0) or 0)
        ratio_product_vs_secondary = float(day_tp.get("ratio_product_vs_secondary", 0) or 0)

        ready_overdue = int(kiln_summary.get("ready_overdue", 0) or 0)
        unloading_overdue = int(kiln_summary.get("unloading_overdue", 0) or 0)
        empty_kilns = int(kiln_summary.get("empty", 0) or 0)

        weakest = stages[0] if stages else {"key": "middle", "name": "中段", "reason": "当前系统判断该环节评分最低。"}
        middle_stage = next((s for s in stages if s.get("key") == "middle"), weakest)

        if (ready_overdue + unloading_overdue) >= 2 and kiln_done_stock <= max(8, int(day_tp.get("secondary_trays", 0) or 0)):
            return {
                "key": "back",
                "name": "后段（二选/出窑承接/成品推进）",
                "reason": (
                    f"症状出现在窑端，但根因更像在窑后承接。完成待出/出窑超时 {ready_overdue + unloading_overdue} 台，"
                    f"而待二选只有 {kiln_done_stock} 托，说明不是窑内继续加工慢，而是出窑后的承接、二选或成品推进不顺。"
                ),
                "symptom_stage": middle_stage.get("name", "中段"),
            }

        if empty_kilns >= 2 and sorting_stock <= 6:
            if dip_stock <= 2 and ratio_dip_vs_saw < 75:
                return {
                    "key": "front",
                    "name": "前段（锯解/药浸）",
                    "reason": (
                        f"空窑 {empty_kilns} 台且待入窑只有 {sorting_stock} 托，说明窑前缺料。"
                        f"同时药浸库存 {dip_stock} 托、今日药浸/锯解转化比 {ratio_dip_vs_saw}%，更像前段供料不足。"
                    ),
                    "symptom_stage": middle_stage.get("name", "中段"),
                }
            return {
                "key": "middle",
                "name": "中段（拣选/入窑衔接）",
                "reason": (
                    f"空窑 {empty_kilns} 台，但锯解库存 {saw_stock} 托不算低，说明不是完全没料，"
                    f"更像药浸后到拣选、入窑这段衔接不足，待入窑只有 {sorting_stock} 托。"
                ),
                "symptom_stage": middle_stage.get("name", "中段"),
            }

        if sorting_stock >= max(12, int(day_tp.get("sort_trays", 0) or 0)):
            return {
                "key": "middle",
                "name": "中段（拣选/入窑/装窑节拍）",
                "reason": (
                    f"待入窑 {sorting_stock} 托偏高，说明前段已把料推上来，但装窑/入窑节拍没有跟上。"
                    f"这更像中段消化能力不足，而不是后段问题。"
                ),
                "symptom_stage": middle_stage.get("name", "中段"),
            }

        if kiln_done_stock >= max(10, int(day_tp.get("secondary_trays", 0) or 0)) and ratio_product_vs_secondary < 92:
            return {
                "key": "back",
                "name": "后段（二选/成品/发货）",
                "reason": (
                    f"待二选 {kiln_done_stock} 托且今日成品/二选转化比只有 {ratio_product_vs_secondary}%，"
                    f"说明出窑后的二选、成品推进或发货承接更该优先提升。"
                ),
                "symptom_stage": "后段（二选/成品/发货）",
            }

        return {
            "key": weakest.get("key", "middle"),
            "name": weakest.get("name", "中段"),
            "reason": weakest.get("reason", "当前系统判断该环节评分最低。"),
            "symptom_stage": weakest.get("name", "中段"),
        }

    def _build_factory_analysis(stock_data: dict, lang: str) -> dict:
        center = get_alert_center_payload(limit_recent=12, lang=lang)
        efficiency = center.get("efficiency", {}) if isinstance(center, dict) else {}
        throughput = center.get("throughput", {}) if isinstance(center, dict) else {}
        analysis = _shared_build_factory_intelligence(stock_data, efficiency, throughput, lang=lang)
        analysis["efficiency"] = efficiency
        analysis["throughput"] = throughput
        analysis["shipping_summary"] = stock_data.get("shipping_summary", {}) if isinstance(stock_data, dict) else {}
        return analysis

    def _build_factory_fallback_answer(question: str, stock_data: dict, lang: str, analysis: dict | None = None) -> str:
        analysis = analysis or _build_factory_analysis(stock_data, lang)
        total_score = analysis.get("efficiency", {}).get("current", {}).get("total_score", 0)
        return _shared_build_factory_fallback_answer(question, analysis, total_score, lang=lang)

    def _build_web_ai_context(stock_data: dict, analysis: dict) -> str:
        return _shared_build_factory_context(stock_data, analysis, analysis.get("efficiency", {}), analysis.get("throughput", {}), lang=get_lang())

    # 中文注释：模块内保留原有重定向行为，避免改动业务返回格式
    def _redirect_index_result(message: str, error: bool = False):
        return redirect(
            url_for(
                "index",
                result=str(message or ""),
                error="1" if error else "0",
                lang=get_lang(),
            ),
            code=303,
        )

    @app.route("/", methods=["GET"])
    @login_required
    def index():
        if str(getattr(current_user, "role", "") or "") == "boss":
            req_lang = (request.args.get("lang") or "").strip()
            target_lang = req_lang if req_lang in LANGUAGES else "zh"
            return redirect(url_for("boss_h5", lang=target_lang))
        stock_data = get_stock_data_with_lang()
        result = request.args.get("result")
        error_flag = str(request.args.get("error", "0")).strip() in ("1", "true", "True")
        return render_template_string(HTML_TEMPLATE, result=result, error=error_flag, **stock_data)

    @app.route("/boss/h5", methods=["GET"])
    @login_required
    def boss_h5():
        if str(getattr(current_user, "role", "") or "") != "boss":
            return redirect(url_for("index", lang=get_lang()))
        req_lang = (request.args.get("lang") or "").strip()
        if req_lang not in LANGUAGES:
            return redirect(url_for("boss_h5", lang="zh"))
        stock_data = get_stock_data_with_lang()
        return render_template_string(BOSS_H5_TEMPLATE, **stock_data)

    @app.route("/api/system/health", methods=["GET"])
    @login_required
    def api_system_health():
        return jsonify(get_system_health_snapshot())

    @app.route("/api/daily_missing_entry_status", methods=["GET"])
    @login_required
    def api_daily_missing_entry_status():
        return jsonify(get_daily_missing_entry_status())

    @app.route("/api/ai-assistant", methods=["POST"])
    @login_required
    def api_ai_assistant():
        payload = request.get_json(silent=True) or request.form
        question = str(payload.get("question") or "").strip()
        if not question:
            return jsonify({"ok": False, "error": "请输入问题"}), 400
        if len(question) > 1000:
            return jsonify({"ok": False, "error": "问题太长，请缩短到 1000 字以内"}), 400

        lang = get_lang()
        use_factory_context = _needs_factory_context(question) and not _is_smalltalk_question(question)
        if use_factory_context:
            stock_data = get_stock_data_with_lang()
            analysis = _build_factory_analysis(stock_data, lang)
            context_text = _build_web_ai_context(stock_data, analysis)
            prompt = (
                "下面是 AIF 网页中的实时经营数据，以及系统对全流程效率的先验判断。\n"
                "预警不是依据，系统全盘判断摘要才是依据。\n"
                "这次用户问的是经营分析类问题，你必须先理解整条生产链，再回答具体问题，不能只抓某一条积压或某一个窑状态。\n"
                "只引用与问题直接相关的数据，不要机械复述整段数据。\n\n"
                f"{context_text}\n\n"
                f"用户问题：{question}\n\n"
                "回答要求："
                "1. 先直接回答用户真正的问题；"
                "2. 至少引用 1 到 3 个和问题直接相关的实际指标、阶段评分、转化比、库存数字或窑状态；"
                "3. 如果用户在问瓶颈、堵点、该先调哪里，必须区分“症状出在哪”和“根因卡在哪”；"
                "4. 如果是在做经营判断，再补 3 条以内建议；"
                "5. 如果数据不足，要直接说缺什么；"
                "6. 不要编造不存在的数字，也不要把预警标题当成结论。"
            )
            system_prompt = (
                "你是 AIF 网页内置 AI 助手。"
                "你的角色不是预警播报器，而是整厂运营分析助理。"
                "你要先看整条链路的节拍，再回答局部问题，还要区分现象和根因。"
                "当用户问经营分析时，要优先基于系统给出的全流程判断摘要作答。"
                "当用户只是打招呼、闲聊或问普通问题时，正常自然回答，不要硬扯库存。"
                "当问题明显是在问当前经营情况时，必须引用当前数据，不允许只给空泛套话。"
                "回答要简洁、具体、有人味。"
            )
            max_tokens = 420
        else:
            prompt = (
                f"用户问题：{question}\n\n"
                "如果这是打招呼、寒暄或普通问题，请自然回答。"
                "如果这是泛化建议题，也可以直接给简洁建议。"
                "不要硬套工厂预警模板。"
            )
            system_prompt = (
                "你是 AIF 网页内置 AI 助手。"
                "你要自然、简洁、像真人助理一样说话。"
                "不要每次都提预警、库存、窑状态，除非用户明确在问这些。"
            )
            max_tokens = 220
        try:
            if use_factory_context:
                try:
                    answer = _structured_ai_factory_answer(question, stock_data, lang, analysis)
                    return jsonify({"ok": True, "answer": answer, "source": "ai_structured"})
                except Exception:
                    logger.exception("web_ai_structured_reasoning_failed")
            answer = ask_ai(prompt, system_prompt=system_prompt, max_tokens=max_tokens)
            if use_factory_context and not _answer_uses_factory_context(answer):
                retry_prompt = (
                    "你刚才的回答太空泛，没有使用当前数据。\n"
                    "现在必须重答，并满足下面要求：\n"
                    "1. 第一行先写“结论：...”\n"
                    "2. 第二部分写“依据：...”，至少引用 2 个当前指标、库存数字或窑状态\n"
                    "3. 第三部分写“建议：...”，最多 3 条\n"
                    "4. 如果问题涉及瓶颈或先调哪里，先区分症状环节和根因环节，再落到结论\n"
                    "5. 不要说“要看情况”或“取决于情况”这类空话\n\n"
                    f"实时数据如下：\n{context_text}\n\n"
                    f"用户问题：{question}"
                )
                answer = ask_ai(retry_prompt, system_prompt=system_prompt, max_tokens=420)
            if use_factory_context and _is_generic_ai_answer(answer):
                answer = _build_factory_fallback_answer(question, stock_data, lang, analysis=analysis)
                return jsonify({"ok": True, "answer": answer, "source": "system_fallback"})
            return jsonify({"ok": True, "answer": answer, "source": "ai_text"})
        except Exception as e:
            logger.exception("web_ai_assistant_failed")
            return jsonify({"ok": False, "error": f"AI 调用失败: {e}"}), 500

    @app.route("/admin/adjust_stock", methods=["POST"])
    @login_required
    def admin_adjust_stock():
        if not current_user.has_permission("admin"):
            return _redirect_index_result(f"❌ {_t('no_admin_perm')}", error=True)

        section = (request.form.get("section") or "").strip()
        try:
            if section == "log":
                value = _to_float(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                _set_raw_log_stock(value)
            elif section == "saw":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["saw_tray_pool"] = value
                _save_flow_data(flow)
            elif section == "byproduct":
                bark_ks = _to_float(request.form.get("bark_stock_ks"), -1)
                dust = _to_int(request.form.get("dust_bag_stock"), -1)
                waste_segment = _to_int(request.form.get("waste_segment_bag_stock"), -1)
                if bark_ks < 0 or dust < 0 or waste_segment < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                # 中文注释：管理员修正副产品库存时，三项库存都直接写入库存池，前后端统一读取该权威值。
                flow["bark_stock_ks_pool"] = bark_ks
                flow["bark_stock_m3"] = bark_ks / BARK_PRICE_PER_M3_KS
                flow["dust_bag_pool"] = dust
                flow["waste_segment_bag_pool"] = waste_segment
                _save_flow_data(flow)
            elif section == "dip":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["dip_tray_pool"] = value
                _save_flow_data(flow)
            elif section == "dip_chem":
                value = _to_float(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["dip_chem_bag_pool"] = value
                _save_flow_data(flow)
            elif section == "sort":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["selected_tray_pool"] = value
                # 兼容：若存在托级明细，库存读取会以明细数量为准；管理员强制改库存时同步明细长度。
                if isinstance(flow.get("selected_tray_details"), list):
                    flow["selected_tray_details"] = [{"id": None, "spec": "?"} for _ in range(value)]
                _save_flow_data(flow)
            elif section == "kiln_done":
                value = _to_int(request.form.get("value"), -1)
                if value < 0:
                    raise ValueError("invalid")
                flow = _read_flow_data()
                flow["kiln_done_tray_pool"] = value
                # 兼容：若存在托级明细，库存读取会以明细数量为准；管理员强制改库存时同步明细长度。
                if isinstance(flow.get("kiln_done_trays"), list):
                    flow["kiln_done_trays"] = [{"id": None, "spec": "?"} for _ in range(value)]
                _save_flow_data(flow)
            else:
                return _redirect_index_result(f"❌ {_t('adjust_invalid_section')}", error=True)
        except Exception:
            return _redirect_index_result(f"❌ {_t('adjust_invalid_value')}", error=True)

        audit_admin_action(
            "adjust_stock",
            target=section,
            detail=str(dict(request.form) or ""),
        )
        return _redirect_index_result(f"✅ {_t('adjust_saved')}", error=False)

    @app.route("/admin/adjust_kiln", methods=["POST"])
    @login_required
    def admin_adjust_kiln():
        if not current_user.has_permission("admin"):
            return _redirect_index_result(f"❌ {_t('no_admin_perm')}", error=True)

        kiln_id = (request.form.get("kiln_id") or "").strip().upper()
        if kiln_id not in ["A", "B", "C", "D"]:
            return _redirect_index_result("❌ invalid kiln id", error=True)

        kilns = _load_kilns_data()
        kiln = kilns.get(kiln_id, {})
        old_status = str(kiln.get("status", "empty") or "empty")
        status_raw = (request.form.get("status") or "").strip()
        status = status_raw or old_status

        valid_status = {"empty", "loading", "drying", "unloading", "ready", "completed"}
        if status not in valid_status:
            return _redirect_index_result("❌ invalid kiln status", error=True)

        def _opt_nonneg(field: str):
            raw = request.form.get(field)
            txt = str(raw or "").strip()
            if txt == "":
                return None
            val = _to_int(txt, -1)
            if val < 0:
                return "invalid"
            return val

        elapsed_hours = _opt_nonneg("elapsed_hours")
        remaining_hours = _opt_nonneg("remaining_hours")
        total_trays = _opt_nonneg("total_trays")
        remaining_trays = _opt_nonneg("remaining_trays")

        if "invalid" in {elapsed_hours, remaining_hours, total_trays, remaining_trays}:
            return _redirect_index_result(f"❌ {_t('adjust_invalid_value')}", error=True)

        kiln["status"] = status
        if old_status != status:
            kiln["status_changed_at"] = int(time.time())
        elif not kiln.get("status_changed_at"):
            kiln["status_changed_at"] = int(time.time())
        kiln.pop("manual_elapsed_hours", None)
        kiln.pop("manual_remaining_hours", None)

        if status == "drying":
            now_ts = int(time.time())
            elapsed_calc_hours = elapsed_hours
            remaining_calc_hours = remaining_hours
            if elapsed_calc_hours is None and remaining_calc_hours is None:
                elapsed_calc_hours = 0 if old_status != "drying" else None
            if elapsed_calc_hours is None and remaining_calc_hours is not None:
                elapsed_calc_hours = max(0, 120 - remaining_calc_hours)
            if elapsed_calc_hours is not None:
                start_ts = max(0, now_ts - max(0, elapsed_calc_hours) * 3600)
                kiln["dry_start"] = start_ts
                kiln["start"] = datetime.fromtimestamp(start_ts).isoformat()
        elif status in {"empty", "loading", "completed"}:
            kiln["dry_start"] = None
            kiln["start"] = None
            if status == "empty":
                kiln["trays"] = []
                kiln["unloaded_count"] = 0
                kiln["unloading_total_trays"] = 0

        if total_trays is not None and status in {"ready", "unloading", "completed"}:
            kiln["unloading_total_trays"] = total_trays
            if remaining_trays is not None:
                remaining_trays = min(remaining_trays, total_trays)
                kiln["unloaded_count"] = max(0, total_trays - remaining_trays)
        elif status in {"loading", "drying"} and (old_status != status):
            tray_list = kiln.get("trays", [])
            auto_total = sum(_to_int(item.get("count"), 0) for item in tray_list) if isinstance(tray_list, list) else 0
            kiln["unloading_total_trays"] = auto_total
            kiln["unloaded_count"] = 0
        elif status == "unloading":
            tray_list = kiln.get("trays", [])
            auto_total = sum(_to_int(item.get("count"), 0) for item in tray_list) if isinstance(tray_list, list) else 0
            if auto_total > 0 and remaining_trays is not None:
                kiln["unloading_total_trays"] = auto_total
                remaining_trays = min(remaining_trays, auto_total)
                kiln["unloaded_count"] = max(0, auto_total - remaining_trays)

        kilns[kiln_id] = kiln
        _save_kilns_data(kilns)

        lang_pack = LANGUAGES.get(get_lang(), LANGUAGES["zh"])
        old_status_label = lang_pack.get(old_status, old_status)
        new_status_label = lang_pack.get(status, status)

        logger.info("admin_adjust_kiln user=%s kiln=%s %s->%s", current_user.username, kiln_id, old_status, status)
        audit_admin_action(
            "adjust_kiln",
            target=kiln_id,
            detail=f"{old_status}->{status}, elapsed={elapsed_hours}, remain_h={remaining_hours}, total={total_trays}, remaining={remaining_trays}",
        )
        return _redirect_index_result(
            f"✅ {_t('kiln_adjust_saved')}（{kiln_id}: {old_status_label} → {new_status_label}）",
            error=False,
        )

    @app.route("/command", methods=["POST"])
    @login_required
    def handle_command():
        command = request.form.get("command", "").strip()
        if not command:
            return _redirect_index_result(_t("enter_command"), error=True)
        try:
            result = dispatch(command) or _t("unknown_cmd")
            return _redirect_index_result(result, error=False)
        except Exception as e:
            return _redirect_index_result(f"❌ {_t('sys_error')}: {str(e)}", error=True)
