"""
Flask Web界面主程序
提供监控系统的Web管理界面
"""

import json
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# 可选依赖：CORS支持
try:
    from flask_cors import CORS
    CORS_AVAILABLE = True
except ImportError:
    CORS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("flask_cors模块未安装，CORS支持已禁用")

from monitor_service import get_monitor_service

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'thinktank_monitor_secret_key_2024'  # 在生产环境中应使用环境变量
if CORS_AVAILABLE:
    CORS(app)  # 启用CORS支持
    logger.info("CORS支持已启用")
else:
    logger.info("CORS支持已禁用")

# 获取监控服务实例
monitor_service = get_monitor_service()


@app.route('/')
def index():
    """首页 - 显示监控状态"""
    try:
        status = monitor_service.get_status()
        return render_template('index.html', status=status)
    except Exception as e:
        logger.error(f"首页加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    """获取监控状态API"""
    try:
        status = monitor_service.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logger.error(f"获取状态API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/start', methods=['POST'])
def api_start():
    """开始监控API"""
    try:
        success = monitor_service.start_monitoring()
        
        if success:
            return jsonify({
                'success': True,
                'message': '监控已启动'
            })
        else:
            return jsonify({
                'success': False,
                'error': '监控启动失败'
            })
            
    except Exception as e:
        logger.error(f"启动监控API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/stop', methods=['POST'])
def api_stop():
    """停止监控API"""
    try:
        success = monitor_service.stop_monitoring()
        
        if success:
            return jsonify({
                'success': True,
                'message': '监控已停止'
            })
        else:
            return jsonify({
                'success': False,
                'error': '监控停止失败'
            })
            
    except Exception as e:
        logger.error(f"停止监控API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/run_once', methods=['POST'])
def api_run_once():
    """运行单次检查API"""
    try:
        results = monitor_service.run_once()
        
        if results:
            return jsonify({
                'success': True,
                'message': '单次检查完成',
                'results': results
            })
        else:
            return jsonify({
                'success': True,
                'message': '检查完成，但可能无新报告或出现错误',
                'results': {}
            })
            
    except Exception as e:
        logger.error(f"单次检查API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/settings', methods=['GET'])
def settings_page():
    """邮箱设置页面"""
    try:
        status = monitor_service.get_status()
        return render_template('settings.html', status=status)
    except Exception as e:
        logger.error(f"设置页面加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """获取设置API"""
    try:
        status = monitor_service.get_status()
        
        # 提取设置相关字段
        settings = {
            'recipient_emails': status.get('recipient_emails', []),
            'check_interval_hours': status.get('check_interval_hours', 2)
        }
        
        return jsonify({
            'success': True,
            'settings': settings
        })
        
    except Exception as e:
        logger.error(f"获取设置API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    """更新设置API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '请求数据为空'
            }), 400
        
        recipient_emails = data.get('recipient_emails')
        check_interval_hours = data.get('check_interval_hours')
        
        success = monitor_service.update_settings(
            recipient_emails=recipient_emails,
            check_interval_hours=check_interval_hours
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': '设置更新成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '设置更新失败'
            })
            
    except Exception as e:
        logger.error(f"更新设置API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/reports', methods=['GET'])
def reports_page():
    """数据查看页面"""
    try:
        # 获取参数
        limit = request.args.get('limit', 20, type=int)
        
        # 参数验证
        if limit < 1 or limit > 100:
            limit = 20
        
        reports = monitor_service.get_recent_reports(limit=limit)
        return render_template('reports.html', reports=reports, limit=limit)
    except Exception as e:
        logger.error(f"报告页面加载失败: {e}")
        return render_template('error.html', error=str(e)), 500


@app.route('/api/reports', methods=['GET'])
def api_get_reports():
    """获取报告数据API"""
    try:
        limit = request.args.get('limit', 20, type=int)
        
        if limit < 1 or limit > 100:
            limit = 20
            
        reports = monitor_service.get_recent_reports(limit=limit)
        
        return jsonify({
            'success': True,
            'reports': reports,
            'count': len(reports)
        })
        
    except Exception as e:
        logger.error(f"获取报告API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/recent_tweets', methods=['GET'])
def api_get_recent_tweets():
    """获取最近推文API"""
    try:
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        # 参数验证
        if days < 1 or days > 365:
            days = 30
        if limit < 1 or limit > 100:
            limit = 20
        
        recent_tweets = monitor_service.get_recent_tweets(days=days, limit=limit)
        
        return jsonify({
            'success': True,
            'tweets': recent_tweets,
            'count': len(recent_tweets),
            'days': days
        })
        
    except Exception as e:
        logger.error(f"获取最近推文API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/send_unsent', methods=['POST'])
def api_send_unsent():
    """发送未发送的报告API"""
    try:
        # 这个功能需要email_sender模块支持
        # 暂时使用run_once，因为它会自动发送新报告的邮件
        # 未来可以扩展monitor_service以支持发送未发送报告
        results = monitor_service.run_once()
        
        return jsonify({
            'success': True,
            'message': '已尝试发送新报告邮件',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"发送未发送报告API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test_email', methods=['POST'])
def api_test_email():
    """发送测试邮件API"""
    try:
        # 调用监控服务的测试邮件发送功能
        result = monitor_service.send_test_email()
        
        # 返回结果
        if result.get('success'):
            return jsonify({
                'success': True,
                'message': result.get('message', '测试邮件发送成功')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', '测试邮件发送失败')
            })
            
    except Exception as e:
        logger.error(f"发送测试邮件API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def page_not_found(e):
    """404错误处理"""
    return render_template('error.html', error='页面未找到'), 404


@app.errorhandler(500)
def internal_server_error(e):
    """500错误处理"""
    logger.error(f"服务器内部错误: {e}")
    return render_template('error.html', error='服务器内部错误'), 500


@app.route('/api/monitor_runs', methods=['GET'])
def api_get_monitor_runs():
    """获取监控运行记录API"""
    try:
        limit = request.args.get('limit', 10, type=int)
        if limit < 1 or limit > 50:
            limit = 10
        
        runs = monitor_service.get_recent_monitor_runs(limit=limit)
        
        # 计算统计信息
        if runs:
            total_runs = len(runs)
            success_runs = sum(1 for r in runs if r.get('status') == 'success')
            avg_duration = sum(r.get('duration_seconds', 0) for r in runs) / total_runs
            total_new_reports = sum(r.get('new_reports_count', 0) for r in runs)
        else:
            total_runs = 0
            success_runs = 0
            avg_duration = 0
            total_new_reports = 0
        
        return jsonify({
            'success': True,
            'runs': runs,
            'stats': {
                'total_runs': total_runs,
                'success_runs': success_runs,
                'success_rate': success_runs / total_runs if total_runs > 0 else 0,
                'avg_duration_seconds': round(avg_duration, 2),
                'total_new_reports': total_new_reports
            }
        })
    except Exception as e:
        logger.error(f"获取监控运行记录API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/monitor_runs', methods=['GET'])
def monitor_runs_page():
    """监控运行记录页面"""
    try:
        runs = monitor_service.get_recent_monitor_runs(limit=10)
        return render_template('monitor_runs.html', runs=runs)
    except Exception as e:
        logger.error(f"监控运行记录页面加载失败: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/tweets', methods=['GET'])
def tweets_page():
    """近期推文页面"""
    try:
        # 获取参数
        days = request.args.get('days', 30, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        # 参数验证
        if days < 1 or days > 365:
            days = 30
        if limit < 1 or limit > 100:
            limit = 20
        
        # 获取最近推文
        tweets = monitor_service.get_recent_tweets(days=days, limit=limit)
        return render_template('tweets.html', tweets=tweets, days=days, limit=limit)
    except Exception as e:
        logger.error(f"近期推文页面加载失败: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/api/smtp_config', methods=['GET'])
def api_get_smtp_config():
    """获取SMTP配置API"""
    try:
        config = monitor_service.get_smtp_config()
        return jsonify(config)
    except Exception as e:
        logger.error(f"获取SMTP配置API失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/trigger-check', methods=['GET'])
def trigger_check():
    """触发监控检查接口（用于外部cron调用）"""
    try:
        logger.info("触发监控检查接口被调用")
        
        # 运行监控检查
        results = monitor_service.run_once()
        
        # 统计结果
        checked_sites = len(results) if results else 0
        new_reports = sum(results.values()) if results else 0
        
        logger.info(f"监控检查完成: 检查了 {checked_sites} 个网站，发现了 {new_reports} 个新报告")
        
        # 返回JSON响应
        return jsonify({
            "status": "success",
            "checked_sites": checked_sites,
            "new_reports": new_reports,
            "results": results if results else {}
        })
        
    except Exception as e:
        logger.error(f"监控检查失败: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # 启动Flask开发服务器（仅用于开发环境）
    # 生产环境应使用WSGI服务器如gunicorn、uWSGI等
    import os
    
    # 从环境变量获取主机和端口，适配Wispbyte等云平台
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    
    print("启动ThinkTank Monitor Web界面...")
    print(f"监听地址: {host}:{port}")
    print(f"访问地址: http://{host}:{port}")
    print("按 Ctrl+C 停止服务器")
    
    app.run(
        host=host,
        port=port,
        debug=False,  # 生产环境禁用调试模式
        threaded=True
    )