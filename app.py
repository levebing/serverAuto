from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, make_response
from flask_cors import CORS
from database import add_server, get_all_servers, get_server_by_id, update_server, delete_server, add_inspection_record, get_inspection_records, get_inspection_record_by_id, get_all_groups, add_group, delete_group, update_group, search_servers
from inspection import ServerInspector
import io
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

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
    servers = []
    if ip:
        servers = search_servers(ip)
    else:
        servers = get_all_servers(group_id)
    groups = get_all_groups()
    return render_template('index.html', servers=servers, groups=groups, selected_group=group_id, search_ip=ip)

@app.route('/records')
def records():
    group_id = request.args.get('group_id', 'all')
    ip = request.args.get('ip', '')
    records = get_inspection_records(group_id=group_id)
    groups = get_all_groups()
    return render_template('records.html', records=records, groups=groups, selected_group=group_id, search_ip=ip)

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
        inspection_result=inspection_result
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
        inspection_result=inspection_result
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
    cursor.execute('DELETE FROM inspection_records WHERE id = ?', (record_id,))
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

def get_connection():
    import sqlite3
    from config import DATABASE_PATH
    return sqlite3.connect(DATABASE_PATH)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)