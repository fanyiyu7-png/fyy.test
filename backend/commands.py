import paramiko

# 服务器字典 - 初始为空，通过界面动态添加
SERVERS = {}

COMMON_COMMANDS = {
    "系统状态": {
        "uptime": "查看系统运行时间/负载",
        "top -bn1 | head -5": "查看资源占用概况",
        "free -h": "查看内存使用情况",
        "df -h": "查看磁盘使用情况",
        "ps aux --sort=-%cpu | head -8": "CPU占用TOP进程",
    },
    "网络相关": {
        "ip addr": "查看网络配置",
        "netstat -tlnp": "查看监听端口",
        "ss -tlnp": "查看监听端口(ss)",
        "ping -c 3 baidu.com": "测试网络连通性",
        "curl -I http://localhost": "测试本地HTTP服务",
    },
    "服务管理": {
        "systemctl status ssh": "SSH服务状态",
        "systemctl status nginx": "Nginx状态",
        "systemctl restart nginx": "重启Nginx",
        "systemctl status mysql": "MySQL状态",
        "systemctl status docker": "Docker状态",
    },
    "Docker相关": {
        "docker ps": "查看运行中的容器",
        "docker ps -a": "查看所有容器",
        "docker images": "查看镜像列表",
        "docker stats --no-stream": "容器资源占用",
    },
    "文件与磁盘": {
        "df -h": "磁盘使用情况",
        "du -sh /* 2>/dev/null | sort -rh | head -10": "根目录占用排名",
        "lsblk": "查看块设备",
        "ls -la /var/log": "查看日志目录",
    },
    "日志查看": {
        "tail -30 /var/log/syslog": "系统日志(30行)",
        "tail -30 /var/log/nginx/error.log": "Nginx错误日志",
        "tail -30 /var/log/mysql/error.log": "MySQL错误日志",
        "dmesg | tail -20": "内核日志",
        "journalctl -xe --no-pager | tail -20": "journal日志",
    },
    "用户相关": {
        "who": "查看在线用户",
        "w": "查看用户活动",
        "last -10": "最近登录记录",
        "cat /etc/passwd | tail -10": "用户列表",
    },
    "系统操作": {
        "reboot": "重启系统",
        "shutdown -h now": "关机",
        "systemctl list-units --type=service | head -20": "服务列表",
        "crontab -l": "查看定时任务",
    }
}

def ssh_connect(server):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=server["host"],
        port=server["port"],
        username=server["username"],
        password=server["password"],
        timeout=5
    )
    return ssh

def exec_cmd(ssh, command):
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def add_server(ip, password, username="root", port=22, name=None):
    """动态添加服务器"""
    server_id = "server-" + ip.replace(".", "-")
    if name is None:
        name = "服务器 (" + ip + ")"
    SERVERS[server_id] = {
        "host": ip,
        "port": port,
        "username": username,
        "password": password,
        "name": name
    }
    return server_id

def remove_server(server_id):
    """移除服务器"""
    if server_id in SERVERS:
        del SERVERS[server_id]
        return True
    return False

def get_remote_stats(server_id):
    server = SERVERS.get(server_id)
    if not server:
        return None
    try:
        ssh = ssh_connect(server)
        
        # CPU - 兼容多种格式
        cpu_out, _ = exec_cmd(ssh, "top -bn1 | grep -E '^(%Cpu|Cpu)' | awk '{print $2}' | cut -d'%' -f1")
        try:
            cpu = round(float(cpu_out), 1)
        except:
            cpu_out2, _ = exec_cmd(ssh, "vmstat 1 2 | tail -1 | awk '{print 100-$15}'")
            try:
                cpu = round(float(cpu_out2), 1)
            except:
                cpu = 0
        
        # 内存
        mem_out, _ = exec_cmd(ssh, "free | grep Mem | awk '{printf \"%.1f\", $3/$2*100}'")
        try:
            memory = round(float(mem_out), 1)
        except:
            memory = 0
        
        # 磁盘
        disk_out, _ = exec_cmd(ssh, "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'")
        try:
            disk = round(float(disk_out), 1)
        except:
            disk = 0
        
        ssh.close()
        return {"cpu": cpu, "memory": memory, "disk": disk, "online": True}
    except Exception as e:
        return {"cpu": 0, "memory": 0, "disk": 0, "online": False, "error": str(e)}

def execute_remote(server_id, command):
    server = SERVERS.get(server_id)
    if not server:
        return {"error": "Server not found"}
    try:
        ssh = ssh_connect(server)
        out, err = exec_cmd(ssh, command)
        ssh.close()
        return {"stdout": out, "stderr": err, "server": server_id}
    except Exception as e:
        return {"error": str(e)}
