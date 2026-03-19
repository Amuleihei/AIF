import logging

from web.route_modules.auth_admin import register_auth_admin_routes
from web.route_modules.reporting import register_reporting_routes
from web.route_support import _t


def register_routes(app):
    logger = logging.getLogger(__name__)
    # 中文注释：先注册认证/管理员路由
    register_auth_admin_routes(app, translate=_t)

    # 中文注释：按业务域分模块注册
    from web.route_modules.inventory_shipping import register_inventory_shipping_routes
    from web.route_modules.operations import register_operations_routes
    from web.route_modules.production_kiln import register_production_kiln_routes

    register_inventory_shipping_routes(app)
    register_operations_routes(app, logger=logger)
    register_production_kiln_routes(app, logger=logger)
    register_reporting_routes(app)
