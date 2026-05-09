from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
from flask_cors import CORS
from database import add_server, get_all_servers, get_server_by_id, update_server, delete_server, add_inspection_record, get_inspection_records, get_inspection_record_by_id, get_all_groups, add_group, delete_group, update_group, search_servers, add_scheduled_task, get_scheduled_task_by_server_id, get_all_scheduled_tasks, update_scheduled_task, delete_scheduled_task, add_report, get_all_reports, delete_report, update_group_sort_order, get_servers_count, get_inspection_records_count, get_scheduled_tasks_count, get_reports_count, add_inspection_item, get_all_inspection_items, get_inspection_item_by_id, update_inspection_item, delete_inspection_item, toggle_inspection_item
from inspection import ServerInspector
import io
from docx import Document
from docx.shared import Pt, RGBColor
import datetime
from docx.enum.text import WD_ALIGN_PARAGRAPH
import base64
import requests
import config

app = Flask(__name__)
CORS(app)

def generate_docx_report(server_name, ip, result):
    doc = Document()
    
    title = doc.add_heading('服务器巡检报告', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    doc.add_paragraph()
    
    info_table = doc.add_table(rows=2, cols=2)
    info_table.style = 'Table Grid'
    info_table.cell(0, 0).text = '服务器名称'
    info_table.cell(0, 1).text = server_name
    info_table.cell(1, 0).text = '服务器IP'
    info_table.cell(1, 1).text = ip
    
    doc.add_paragraph()
    
    doc.add_heading('一、巡检时间', level=2)
    doc.add_paragraph(f"巡检时间: {result['inspection_time']}")
    doc.add_paragraph(f"系统时间: {result['system_time']}")
    
    doc.add_heading('二、操作系统信息', level=2)
    os_info = result['os_version'] or '无法获取操作系统版本'
    doc.add_paragraph(os_info)
    
    doc.add_heading('三、CPU使用率', level=2)
    cpu_usage = result['cpu_usage'] or '无法获取'
    doc.add_paragraph(f"CPU使用率: {cpu_usage}%")
    
    doc.add_heading('四、内存使用情况', level=2)
    memory_info = eval(result['memory_usage']) if result['memory_usage'] else {}
    if memory_info:
        memory_table = doc.add_table(rows=4, cols=2)
        memory_table.style = 'Table Grid'
        memory_table.cell(0, 0).text = '总计'
        memory_table.cell(0, 1).text = memory_info.get('total', '未知')
        memory_table.cell(1, 0).text = '已用'
        memory_table.cell(1, 1).text = memory_info.get('used', '未知')
        memory_table.cell(2, 0).text = '可用'
        memory_table.cell(2, 1).text = memory_info.get('available', '未知')
        memory_table.cell(3, 0).text = '使用率'
        usage_percent = memory_info.get('usage_percent', '未知')
        memory_table.cell(3, 1).text = f"{usage_percent}%"
        if isinstance(usage_percent, int) and usage_percent >= 80:
            memory_table.cell(3, 1).paragraphs[0].runs[0].font.color.rgb = RGBColor(220, 53, 69)
    else:
        doc.add_paragraph('无法获取内存信息')
    
    doc.add_heading('五、磁盘使用情况', level=2)
    disk_info = eval(result['disk_usage']) if result['disk_usage'] else []
    if disk_info:
        disk_table = doc.add_table(rows=len(disk_info) + 1, cols=5)
        disk_table.style = 'Table Grid'
        headers = ['挂载点', '文件系统', '总计', '已用', '使用率']
        for i, header in enumerate(headers):
            disk_table.cell(0, i).text = header
            disk_table.cell(0, i).paragraphs[0].runs[0].font.bold = True
        
        for i, disk in enumerate(disk_info, 1):
            disk_table.cell(i, 0).text = disk.get('mount_point', '')
            disk_table.cell(i, 1).text = disk.get('filesystem', '')
            disk_table.cell(i, 2).text = disk.get('size', '')
            disk_table.cell(i, 3).text = disk.get('used', '')
            usage = disk.get('usage_percent', 0)
            disk_table.cell(i, 4).text = f"{usage}%"
            if usage >= 80:
                disk_table.cell(i, 4).paragraphs[0].runs[0].font.color.rgb = RGBColor(220, 53, 69)
    else:
        doc.add_paragraph('无法获取磁盘信息')
    
    doc.add_heading('六、告警内容', level=2)
    alert_content = result['alert_content']
    alert_paragraph = doc.add_paragraph(alert_content)
    if alert_content != '无告警':
        alert_paragraph.runs[0].font.color.rgb = RGBColor(220, 53, 69)
        alert_paragraph.runs[0].font.bold = True
    else:
        alert_paragraph.runs[0].font.color.rgb = RGBColor(34, 197, 94)
    
    footer = doc.sections[0].footer
    footer_paragraph = footer.add_paragraph()
    footer_paragraph.text = "服务器自动巡检工具生成"
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    return doc

@app.route('/')
def index():
    group_id = request.args.get('group_id', 'all')
    ip = request.args.get('ip', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    servers = []
    total = 0
    if ip:
        servers = search_servers(ip)
        total = len(servers)
    else:
        servers = get_all_servers(group_id, page, per_page)
        total = get_servers_count(group_id)
    total_pages = (total + per_page - 1) // per_page
    groups = get_all_groups()
    return render_template('index.html', servers=servers, groups=groups, selected_group=group_id, search_ip=ip, page=page, per_page=per_page, total=total, total_pages=total_pages)

@app.route('/records')
def records():
    group_id = request.args.get('group_id', 'all')
    ip = request.args.get('ip', '')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    records = get_inspection_records(group_id=group_id, page=page, per_page=per_page)
    total = get_inspection_records_count(group_id=group_id)
    total_pages = (total + per_page - 1) // per_page
    groups = get_all_groups()
    return render_template('records.html', records=records, groups=groups, selected_group=group_id, search_ip=ip, page=page, per_page=per_page, total=total, total_pages=total_pages)

@app.route('/add', methods=['GET', 'POST'])
def add():
    groups = get_all_groups()
    if request.method == 'POST':
        name = request.form['name']
        ip = request.form['ip']
        port = int(request.form['port'])
        username = request.form['username']
        group_id = int(request.form.get('group_id', 1))
        remark = request.form.get('remark', '')
        private_key_content = None
        password = None
        
        if 'private_key' in request.files:
            key_file = request.files['private_key']
            if key_file.filename != '':
                private_key_content = key_file.read()
        
        if not private_key_content:
            password = request.form.get('password')
        
        add_server(name, ip, port, username, group_id, remark, private_key_content, password)
        return redirect(url_for('index'))
    
    return render_template('add.html', groups=groups)

@app.route('/edit/<int:server_id>', methods=['GET', 'POST'])
def edit(server_id):
    server = get_server_by_id(server_id)
    groups = get_all_groups()
    if not server:
        return "服务器不存在", 404
    
    if request.method == 'POST':
        name = request.form['name']
        ip = request.form['ip']
        port = int(request.form['port'])
        username = request.form['username']
        group_id = int(request.form.get('group_id', 1))
        remark = request.form.get('remark', '')
        private_key_content = server[5]
        password = server[6]
        
        if 'private_key' in request.files:
            key_file = request.files['private_key']
            if key_file.filename != '':
                private_key_content = key_file.read()
        
        if not private_key_content:
            password = request.form.get('password')
        
        update_server(server_id, name, ip, port, username, group_id, remark, private_key_content, password)
        return redirect(url_for('index'))
    
    return render_template('edit.html', server=server, groups=groups)

@app.route('/delete/<int:server_id>')
def delete(server_id):
    delete_server(server_id)
    return redirect(url_for('index'))

@app.route('/inspect/<int:server_id>')
def inspect(server_id):
    server = get_server_by_id(server_id)
    if not server:
        return "服务器不存在", 404
    
    inspector = ServerInspector(
        ip=server[2],
        port=server[3],
        username=server[4],
        private_key_content=server[5],
        password=server[6]
    )
    
    result, error = inspector.inspect()
    
    if error:
        groups = get_all_groups()
        return render_template('inspect.html', server=server, error=error, groups=groups)
    
    inspection_result = generate_inspection_result(result)
    
    add_inspection_record(
        server_id=server_id,
        disk_usage=result['disk_usage'],
        memory_usage=result['memory_usage'],
        cpu_usage=result['cpu_usage'],
        system_time=result['system_time'],
        os_version=result['os_version'],
        alert_content=result['alert_content'],
        report_content=str(result),
        inspection_result=inspection_result,
        inspection_time=result['inspection_time']
    )
    
    groups = get_all_groups()
    return render_template('inspect.html', server=server, result=result, groups=groups)

def generate_inspection_result(result):
    """生成巡检结果摘要"""
    items = []
    
    cpu = result.get('cpu_usage')
    if cpu:
        items.append(f"CPU {cpu}%")
    
    memory = result.get('memory_usage')
    if memory:
        try:
            mem_info = eval(memory)
            if mem_info.get('usage_percent'):
                items.append(f"内存 {mem_info['usage_percent']}%")
        except:
            pass
    
    disk = result.get('disk_usage')
    if disk:
        try:
            disk_info = eval(disk)
            for d in disk_info:
                if d.get('usage_percent'):
                    items.append(f"{d['mount_point']} {d['usage_percent']}%")
        except:
            pass
    
    # 添加自定义巡检项的结果
    custom_results = result.get('custom_results', {})
    predefined_items = ['CPU使用率', '内存使用情况', '磁盘使用情况', '系统时间', '操作系统版本']
    for name, output in custom_results.items():
        if name not in predefined_items and output:
            # 对于自定义巡检项，检查是否有运行结果
            if output.strip():
                items.append(f"{name}: 运行中")
            else:
                items.append(f"{name}: 未运行")
    
    alert = result.get('alert_content')
    if alert and alert != '无告警':
        status = '⚠️ 告警'
    else:
        status = '✅ 正常'
    
    return f"{status} | {', '.join(items)}"

@app.route('/api/inspect_async/<int:server_id>', methods=['POST'])
def inspect_async(server_id):
    server = get_server_by_id(server_id)
    if not server:
        return jsonify({'success': False, 'message': '服务器不存在'})
    
    inspector = ServerInspector(
        ip=server[2],
        port=server[3],
        username=server[4],
        private_key_content=server[5],
        password=server[6]
    )
    
    result, error = inspector.inspect()
    
    if error:
        return jsonify({'success': False, 'message': error})
    
    inspection_result = generate_inspection_result(result)
    
    add_inspection_record(
        server_id=server_id,
        disk_usage=result['disk_usage'],
        memory_usage=result['memory_usage'],
        cpu_usage=result['cpu_usage'],
        system_time=result['system_time'],
        os_version=result['os_version'],
        alert_content=result['alert_content'],
        report_content=str(result),
        inspection_result=inspection_result,
        inspection_time=result['inspection_time']
    )
    
    return jsonify({
        'success': True,
        'server_name': server[1],
        'server_ip': server[2],
        'inspection_result': inspection_result,
        'inspection_time': result['inspection_time']
    })

@app.route('/download_report/<int:record_id>')
def download_report(record_id):
    record = get_inspection_record_by_id(record_id)
    if not record:
        return "记录不存在", 404
    
    server = get_server_by_id(record[1])
    server_name = server[1] if server else "unknown"
    server_ip = server[2] if server else "unknown"
    
    try:
        result = eval(record[9]) if record[9] else {}
    except:
        result = {}
    
    result['inspection_time'] = record[7]
    result['system_time'] = record[5]
    result['os_version'] = record[6]
    result['cpu_usage'] = record[4]
    result['memory_usage'] = record[3]
    result['disk_usage'] = record[2]
    result['alert_content'] = record[8] if record[8] else '无告警'
    
    doc = generate_docx_report(server_name, server_ip, result)
    
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    
    filename = f"巡检报告_{server_name}_{record[8]}.docx"
    
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

@app.route('/delete_record/<int:record_id>')
def delete_record(record_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE inspection_records SET is_deleted = 1 WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('records'))

@app.route('/api/add_group', methods=['POST'])
def api_add_group():
    name = request.json.get('name')
    if name:
        group_id = add_group(name)
        if group_id:
            return jsonify({'success': True, 'group_id': group_id, 'name': name})
        else:
            return jsonify({'success': False, 'message': '分组名称已存在'})
    return jsonify({'success': False, 'message': '分组名称不能为空'})

@app.route('/api/delete_group/<int:group_id>')
def api_delete_group(group_id):
    if group_id == 1:
        return jsonify({'success': False, 'message': '不能删除默认分组'})
    delete_group(group_id)
    return jsonify({'success': True})

@app.route('/api/update_group', methods=['POST'])
def api_update_group():
    group_id = request.json.get('group_id')
    name = request.json.get('name')
    if not group_id or not name:
        return jsonify({'success': False, 'message': '参数不能为空'})
    if int(group_id) == 1:
        return jsonify({'success': False, 'message': '不能修改默认分组名称'})
    result = update_group(group_id, name)
    if result is None:
        return jsonify({'success': False, 'message': '分组名称已存在'})
    elif result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '分组不存在'})

@app.route('/api/update_group_sort', methods=['POST'])
def api_update_group_sort():
    group_id = request.json.get('group_id')
    sort_order = request.json.get('sort_order')
    if not group_id or sort_order is None:
        return jsonify({'success': False, 'message': '参数不能为空'})
    result = update_group_sort_order(group_id, sort_order)
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '分组不存在'})

@app.route('/groups')
def groups():
    groups = get_all_groups()
    return render_template('groups.html', groups=groups)

@app.route('/tasks')
def tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    tasks = get_all_scheduled_tasks(page, per_page)
    total = get_scheduled_tasks_count()
    total_pages = (total + per_page - 1) // per_page
    servers = get_all_servers()
    groups = get_all_groups()
    return render_template('tasks.html', tasks=tasks, servers=servers, groups=groups, page=page, per_page=per_page, total=total, total_pages=total_pages)

@app.route('/api/add_task', methods=['POST'])
def api_add_task():
    server_id = request.json.get('server_id')
    cron_expression = request.json.get('cron_expression')
    is_enabled = request.json.get('is_enabled', 1)
    
    if not server_id or not cron_expression:
        return jsonify({'success': False, 'message': '参数不能为空'})
    
    task_id = add_scheduled_task(server_id, cron_expression, is_enabled)
    if task_id:
        return jsonify({'success': True, 'task_id': task_id})
    else:
        return jsonify({'success': False, 'message': '添加任务失败'})

@app.route('/api/update_task', methods=['POST'])
def api_update_task():
    task_id = request.json.get('task_id')
    cron_expression = request.json.get('cron_expression')
    is_enabled = request.json.get('is_enabled')
    
    if not task_id or not cron_expression:
        return jsonify({'success': False, 'message': '参数不能为空'})
    
    result = update_scheduled_task(task_id, cron_expression, is_enabled)
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '更新任务失败'})

@app.route('/api/delete_task/<int:server_id>')
def api_delete_task(server_id):
    delete_scheduled_task(server_id)
    return jsonify({'success': True})

@app.route('/api/delete_report/<int:report_id>')
def api_delete_report(report_id):
    result = delete_report(report_id)
    return jsonify({'success': result})

# 巡检项管理路由
@app.route('/inspection_items')
def inspection_items():
    items = get_all_inspection_items()
    return render_template('inspection_items.html', inspection_items=items)

@app.route('/api/add_inspection_item', methods=['POST'])
def api_add_inspection_item():
    name = request.json.get('name')
    command = request.json.get('command')
    description = request.json.get('description', '')
    
    if not name or not command:
        return jsonify({'success': False, 'message': '名称和命令不能为空'})
    
    item_id = add_inspection_item(name, command, description)
    if item_id:
        return jsonify({'success': True, 'item_id': item_id})
    else:
        return jsonify({'success': False, 'message': '添加失败'})

@app.route('/api/update_inspection_item', methods=['POST'])
def api_update_inspection_item():
    item_id = request.json.get('id')
    name = request.json.get('name')
    command = request.json.get('command')
    description = request.json.get('description', '')
    
    if not item_id or not name or not command:
        return jsonify({'success': False, 'message': '参数不能为空'})
    
    result = update_inspection_item(item_id, name, command, description)
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '更新失败'})

@app.route('/api/delete_inspection_item/<int:item_id>')
def api_delete_inspection_item(item_id):
    result = delete_inspection_item(item_id)
    return jsonify({'success': result})

@app.route('/api/toggle_inspection_item', methods=['POST'])
def api_toggle_inspection_item():
    item_id = request.json.get('id')
    is_enabled = request.json.get('is_enabled')
    
    if item_id is None or is_enabled is None:
        return jsonify({'success': False, 'message': '参数不能为空'})
    
    result = toggle_inspection_item(item_id, is_enabled)
    if result:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': '操作失败'})

@app.route('/reports')
def reports():
    groups = get_all_groups()
    
    # 获取筛选参数
    filter_type = request.args.get('report_type')
    filter_group = request.args.get('group_id')
    filter_date = request.args.get('date')
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # 获取报告列表
    reports = get_all_reports(filter_type, filter_group, filter_date, page, per_page)
    total = get_reports_count(filter_type, filter_group, filter_date)
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('reports.html', groups=groups, reports=reports, 
                           filter_type=filter_type, filter_group=filter_group, filter_date=filter_date, 
                           page=page, per_page=per_page, total=total, total_pages=total_pages, 
                           base_url=config.REPORT_STORAGE['base_url'])

@app.route('/api/generate_report', methods=['POST'])
def api_generate_report():
    report_type = request.json.get('report_type')
    group_id = request.json.get('group_id')
    start_date_str = request.json.get('start_date')
    
    if not report_type or not group_id:
        return jsonify({'success': False, 'message': '参数不能为空'})
    
    # 根据报告类型和分组生成报告
    records = get_inspection_records(group_id=group_id)
    
    # 生成报告内容
    report_content = generate_report_content(records, report_type, start_date_str)
    
    # 生成文件名
    import datetime
    now = datetime.datetime.now()
    filename = f"{report_type}_report_{now.strftime('%Y%m%d_%H%M%S')}.docx"
    
    # 获取分组名称
    group_name = '所有分组' if group_id == 'all' else None
    if group_id != 'all':
        groups = get_all_groups()
        for group in groups:
            if str(group[0]) == group_id:
                group_name = group[1]
                break
    
    # 生成报告名称
    report_name = report_content['title']
    
    # 生成Word文档
    doc = generate_report_docx(report_content, report_type)
    
    # 保存到内存
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    
    # 上传文件到文件服务器
    file_path = None
    try:
        # 重置文件指针
        output.seek(0)
        
        # 调用文件上传服务（使用formData格式）
        upload_url = config.FILE_UPLOAD_SERVICE['url']
        print(f"开始上传文件到: {upload_url}")
        print(f"文件名: {filename}")
        
        # 构建formData
        files = {'files': (filename, output, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        
        # 发送请求
        response = requests.post(upload_url, files=files, timeout=config.FILE_UPLOAD_SERVICE['timeout'])
        
        print(f"上传响应状态码: {response.status_code}")
        print(f"上传响应内容: {response.text}")
        
        # 解析上传响应
        if response.status_code == 200:
            try:
                upload_result = response.json()
                print(f"上传结果: {upload_result}")
                # 从响应中获取文件路径
                if upload_result.get('code') == 200 and upload_result.get('data'):
                    # 假设data是一个数组，取第一个元素
                    if isinstance(upload_result['data'], list) and upload_result['data']:
                        file_path = upload_result['data'][0]
                        print(f"获取到的文件路径: {file_path}")
                    elif isinstance(upload_result['data'], str):
                        file_path = upload_result['data']
                        print(f"获取到的文件路径: {file_path}")
            except Exception as json_error:
                print(f"解析响应JSON失败: {json_error}")
        else:
            print(f"上传失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"文件上传失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 无论上传是否成功，都继续生成报告
    print(f"文件路径: {file_path}")
    
    # 添加报告记录到数据库
    add_report(report_type, group_id if group_id != 'all' else None, group_name, report_name, file_path)
    
    # 重置文件指针
    output.seek(0)
    
    # 返回文件下载响应
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

def generate_report_content(records, report_type, start_date_str=None):
    """生成报告内容"""
    import datetime
    
    # 解析开始时间
    if start_date_str:
        now = datetime.datetime.fromisoformat(start_date_str)
    else:
        now = datetime.datetime.now()
    
    # 根据报告类型确定时间范围
    if report_type == 'daily':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        title = f"服务器巡检日报 ({start_date.strftime('%Y-%m-%d')})"
    elif report_type == 'weekly':
        # 计算本周的开始和结束日期
        start_date = now - datetime.timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
        title = f"服务器巡检周报 ({start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')})"
    elif report_type == 'monthly':
        # 计算本月的开始和结束日期
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1, day=1) - datetime.timedelta(seconds=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1, day=1) - datetime.timedelta(seconds=1)
        title = f"服务器巡检月报 ({start_date.strftime('%Y-%m')})"
    else:
        return None
    
    # 筛选时间范围内的记录
    filtered_records = []
    for record in records:
        inspection_time = datetime.datetime.fromisoformat(record[7])
        if start_date <= inspection_time <= end_date:
            filtered_records.append(record)
    
    # 按服务器IP分组
    server_records = {}
    # 存储所有服务器IP，用于去重
    server_ips = set()
    for record in filtered_records:
        # 尝试获取服务器IP
        server_ip = None
        if len(record) > 10:
            for idx in range(9, min(len(record), 15)):
                if isinstance(record[idx], str):
                    import re
                    ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
                    if re.match(ip_pattern, record[idx]):
                        server_ip = record[idx]
                        server_ips.add(server_ip)
                        break
        
        # 如果没有找到IP，使用服务器名称或其他标识符
        if not server_ip:
            server_ip = record[9] or record[10] or 'unknown'
            server_ips.add(server_ip)
        
        if server_ip not in server_records:
            server_records[server_ip] = []
        server_records[server_ip].append(record)
    
    return {
        'title': title,
        'start_date': start_date,
        'end_date': end_date,
        'server_records': server_records,
        'total_servers': len(server_ips),
        'total_inspections': len(filtered_records)
    }

def generate_report_docx(report_content, report_type):
    """生成报告Word文档"""
    doc = Document()
    
    # 添加标题
    title = doc.add_heading(report_content['title'], level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # 添加报告信息
    doc.add_paragraph()
    info_table = doc.add_table(rows=3, cols=2)
    info_table.style = 'Table Grid'
    info_table.cell(0, 0).text = '报告类型'
    info_table.cell(0, 1).text = {'daily': '日报', 'weekly': '周报', 'monthly': '月报'}.get(report_type, '未知')
    info_table.cell(1, 0).text = '开始时间'
    info_table.cell(1, 1).text = report_content['start_date'].strftime('%Y-%m-%d %H:%M:%S')
    info_table.cell(2, 0).text = '结束时间'
    info_table.cell(2, 1).text = report_content['end_date'].strftime('%Y-%m-%d %H:%M:%S')
    
    # 添加统计信息
    doc.add_paragraph()
    doc.add_heading('一、统计信息', level=2)
    doc.add_paragraph(f"巡检服务器数量: {report_content['total_servers']}")
    doc.add_paragraph(f"巡检次数: {report_content['total_inspections']}")
    
    # 添加服务器巡检详情
    doc.add_paragraph()
    doc.add_heading('二、服务器巡检详情', level=2)
    
    # 收集所有巡检记录
    all_records = []
    for server_name, records in report_content['server_records'].items():
        all_records.extend(records)
    
    # 添加巡检记录表格
    if all_records:
        table = doc.add_table(rows=len(all_records) + 1, cols=8)
        table.style = 'Table Grid'
        
        # 添加表头
        headers = ['序号', '服务器IP', '服务器名称', '巡检时间', 'CPU使用率', '内存使用率', '磁盘使用率', '状态']
        for col_idx, header in enumerate(headers):
            table.cell(0, col_idx).text = header
            table.cell(0, col_idx).paragraphs[0].runs[0].font.bold = True
        
        # 添加数据
        for row_idx, record in enumerate(all_records, 1):
            # 确保行索引不超出表格范围
            if row_idx < len(table.rows):
                table.cell(row_idx, 0).text = str(row_idx)  # 序号
                # 直接使用固定的索引位置获取服务器信息
                # 根据get_inspection_records函数的SQL查询，返回字段顺序为：
                # ir.*, s.name as server_name, s.ip as server_ip, g.name as group_name
                server_ip = '未知'
                server_name = '未知'
                
                # 检查记录长度，确保有足够的字段
                # 根据get_inspection_records函数的SQL查询，返回字段顺序为：
                # ir.*(12个字段) + s.name(服务器名称) + s.ip(服务器IP) + g.name(分组名称)
                if len(record) >= 15:
                    # 服务器名称在索引12，服务器IP在索引13
                    if len(record) > 12 and record[12]:
                        server_name = str(record[12])
                    if len(record) > 13 and record[13]:
                        server_ip = str(record[13])
                
                # 如果还是没有获取到服务器IP，尝试从记录中提取
                if server_ip == '未知':
                    # 尝试从描述字段中提取IP
                    if len(record) > 4 and isinstance(record[4], str):
                        import re
                        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                        match = re.search(ip_pattern, record[4])
                        if match:
                            server_ip = match.group(0)
                
                # 确保列索引不超出表格范围
                if len(table.columns) >= 8:
                    table.cell(row_idx, 1).text = server_ip  # 服务器IP
                    table.cell(row_idx, 2).text = server_name  # 服务器名称
                    table.cell(row_idx, 3).text = record[7]  # 巡检时间
                    table.cell(row_idx, 4).text = f"{record[4]}%" if record[4] else '无法获取'  # CPU使用率
                    
                    # 内存使用率
                    memory_usage = '无法获取'
                    if record[3]:
                        try:
                            mem_info = eval(record[3])
                            if mem_info.get('usage_percent'):
                                memory_usage = f"{mem_info['usage_percent']}%"
                        except:
                            pass
                    table.cell(row_idx, 5).text = memory_usage
                    
                    # 磁盘使用率
                    disk_usage = '无法获取'
                    if record[2]:
                        try:
                            disk_info = eval(record[2])
                            if disk_info:
                                max_usage = max([d.get('usage_percent', 0) for d in disk_info])
                                disk_usage = f"{max_usage}%"
                        except:
                            pass
                    table.cell(row_idx, 6).text = disk_usage
                    
                    # 状态
                    status = '正常'
                    if record[8] and record[8] != '无告警':
                        status = '告警'
                    table.cell(row_idx, 7).text = status
                    
                    # 高亮告警行
                    if status == '告警':
                        for col_idx in range(8):
                            table.cell(row_idx, col_idx).paragraphs[0].runs[0].font.color.rgb = RGBColor(220, 53, 69)
        
    # 添加总结
    doc.add_paragraph()
    doc.add_heading('三、总结', level=2)
    
    # 统计告警次数
    alert_count = 0
    for records in report_content['server_records'].values():
        for record in records:
            if record[8] and record[8] != '无告警':
                alert_count += 1
    
    if alert_count == 0:
        doc.add_paragraph('所有服务器运行正常，未发现告警。')
    else:
        doc.add_paragraph(f'共发现 {alert_count} 次告警，需要关注。')
    
    # 添加页脚
    footer = doc.sections[0].footer
    footer_paragraph = footer.add_paragraph()
    footer_paragraph.text = "服务器自动巡检系统生成"
    footer_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    return doc

def get_connection():
    import sqlite3
    from config import DATABASE_PATH
    return sqlite3.connect(DATABASE_PATH)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=config.PORT)