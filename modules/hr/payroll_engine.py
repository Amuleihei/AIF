from modules.hr.hr_engine import handle_hr


def handle_payroll(text):
    # TG 旧工资录入命令已下线：统一走新 HR 核心指令体系。
    return handle_hr(text)
