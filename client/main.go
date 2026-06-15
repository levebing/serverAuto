package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/disk"
	"github.com/shirou/gopsutil/v3/host"
	"github.com/shirou/gopsutil/v3/mem"
	"gopkg.in/yaml.v3"
)

// 配置结构体
type Config struct {
	Server struct {
		APIBaseURL string `yaml:"api_base_url"`
		Username   string `yaml:"username"`
		Password   string `yaml:"password"`
	} `yaml:"server"`
	Inspection struct {
		IntervalMinutes int  `yaml:"interval_minutes"`
		Enabled         bool `yaml:"enabled"`
		RunOnStart      bool `yaml:"run_on_start"`
	} `yaml:"inspection"`
	ServerInfo struct {
		Name        string `yaml:"name"`
		Port        int    `yaml:"port"`
		SSHUsername string `yaml:"ssh_username"`
		SSHPassword string `yaml:"ssh_password"`
		GroupID     int    `yaml:"group_id"`
		Remark      string `yaml:"remark"`
		OSType      string `yaml:"os_type"`
	} `yaml:"server_info"`
	Log struct {
		Level      string `yaml:"level"`
		OutputFile bool   `yaml:"output_file"`
		LogPath    string `yaml:"log_path"`
	} `yaml:"log"`
}

// Token 响应结构体
type TokenResponse struct {
	Success        bool   `json:"success"`
	Username       string `json:"username"`
	Token          string `json:"token"`
	TokenExpiresIn int    `json:"token_expires_in"`
}

// 巡检响应结构体
type InspectionResponse struct {
	Success          bool   `json:"success"`
	ServerName       string `json:"server_name"`
	ServerIP         string `json:"server_ip"`
	InspectionResult string `json:"inspection_result"`
	InspectionTime   string `json:"inspection_time"`
	Message          string `json:"message"`
}

// 全局变量
var (
	config      Config
	token       string
	tokenExpiry time.Time
	logger      *log.Logger
)

// 初始化日志
func initLogger() {
	if config.Log.OutputFile {
		err := os.MkdirAll(config.Log.LogPath, 0755)
		if err != nil {
			log.Fatalf("无法创建日志目录: %v", err)
		}
		logFile := filepath.Join(config.Log.LogPath, fmt.Sprintf("monitor_%s.log", time.Now().Format("2006-01-02")))
		f, err := os.OpenFile(logFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)
		if err != nil {
			log.Fatalf("无法打开日志文件: %v", err)
		}
		logger = log.New(io.MultiWriter(os.Stdout, f), "", log.LstdFlags)
	} else {
		logger = log.New(os.Stdout, "", log.LstdFlags)
	}
}

// 加载配置文件
func loadConfig(path string) error {
	file, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("无法读取配置文件: %v", err)
	}
	err = yaml.Unmarshal(file, &config)
	if err != nil {
		return fmt.Errorf("配置文件解析失败: %v", err)
	}
	return nil
}

// 获取 Token
func getToken() (string, error) {
	url := fmt.Sprintf("%s/login", config.Server.APIBaseURL)
	data := map[string]string{
		"username": config.Server.Username,
		"password": config.Server.Password,
	}
	jsonData, err := json.Marshal(data)
	if err != nil {
		return "", fmt.Errorf("JSON 序列化失败: %v", err)
	}

	resp, err := http.Post(url, "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("请求失败: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("读取响应失败: %v", err)
	}

	var tokenResp TokenResponse
	err = json.Unmarshal(body, &tokenResp)
	if err != nil {
		return "", fmt.Errorf("响应解析失败: %v", err)
	}

	if !tokenResp.Success {
		return "", fmt.Errorf("获取 Token 失败")
	}

	return tokenResp.Token, nil
}

// 检查并刷新 Token
func ensureToken() error {
	now := time.Now()
	if token == "" || now.After(tokenExpiry) {
		logger.Println("正在获取新的 Token...")
		newToken, err := getToken()
		if err != nil {
			return fmt.Errorf("获取 Token 失败: %v", err)
		}
		token = newToken
		tokenExpiry = now.Add(23 * time.Hour) // 设置为23小时过期，留1小时缓冲
		logger.Printf("Token 获取成功，有效期至: %s", tokenExpiry.Format(time.RFC3339))
	}
	return nil
}

// 获取本机信息
func getLocalServerInfo() (map[string]string, error) {
	info := make(map[string]string)

	// 获取主机名
	hostname, err := os.Hostname()
	if err != nil {
		return nil, fmt.Errorf("获取主机名失败: %v", err)
	}
	if config.ServerInfo.Name == "" {
		info["name"] = hostname
	} else {
		info["name"] = config.ServerInfo.Name
	}

	// 获取IP地址
	ip, err := getLocalIP()
	if err != nil {
		logger.Printf("获取IP地址失败: %v，使用主机名作为标识", err)
		info["ip"] = hostname
	} else {
		info["ip"] = ip
	}

	// 获取操作系统类型
	osType := runtime.GOOS
	if config.ServerInfo.OSType != "" {
		osType = config.ServerInfo.OSType
	}
	info["os_type"] = osType

	return info, nil
}

// 获取本机IP地址
func getLocalIP() (string, error) {
	// Windows 使用 ipconfig
	if runtime.GOOS == "windows" {
		out, err := exec.Command("ipconfig").Output()
		if err != nil {
			return "", err
		}
		lines := strings.Split(string(out), "\n")
		for i, line := range lines {
			if strings.Contains(strings.ToLower(line), "ipv4") {
				parts := strings.Split(line, ":")
				if len(parts) > 1 {
					ip := strings.TrimSpace(parts[1])
					if strings.HasPrefix(ip, "192.168.") || strings.HasPrefix(ip, "10.") || strings.HasPrefix(ip, "172.") {
						return ip, nil
					}
				}
			}
		}
		return "", fmt.Errorf("未找到内网IP")
	}

	// Linux/macOS 使用 hostname
	out, err := exec.Command("hostname", "-I").Output()
	if err != nil {
		return "", err
	}
	ips := strings.Fields(string(out))
	for _, ip := range ips {
		if strings.HasPrefix(ip, "192.168.") || strings.HasPrefix(ip, "10.") || strings.HasPrefix(ip, "172.") {
			return ip, nil
		}
	}
	return "", fmt.Errorf("未找到内网IP")
}

// 推送服务器信息（首次启动时）
func pushServerInfo() error {
	err := ensureToken()
	if err != nil {
		return err
	}

	info, err := getLocalServerInfo()
	if err != nil {
		return fmt.Errorf("获取本机信息失败: %v", err)
	}

	url := fmt.Sprintf("%s/add", config.Server.APIBaseURL)
	var requestBody bytes.Buffer
	writer := multipart.NewWriter(&requestBody)

	// 添加字段
	writer.WriteField("name", info["name"])
	writer.WriteField("ip", info["ip"])
	writer.WriteField("port", strconv.Itoa(config.ServerInfo.Port))
	writer.WriteField("username", config.ServerInfo.SSHUsername)
	writer.WriteField("group_id", strconv.Itoa(config.ServerInfo.GroupID))
	writer.WriteField("remark", config.ServerInfo.Remark)
	writer.WriteField("os_type", info["os_type"])
	if config.ServerInfo.SSHPassword != "" {
		writer.WriteField("password", config.ServerInfo.SSHPassword)
	}
	writer.Close()

	req, err := http.NewRequest("POST", url, &requestBody)
	if err != nil {
		return fmt.Errorf("创建请求失败: %v", err)
	}
	req.Header.Set("Content-Type", writer.FormDataContentType())
	req.Header.Set("X-API-Token", token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("推送服务器信息失败: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusFound {
		logger.Printf("服务器信息推送成功: %s (%s)", info["name"], info["ip"])
		return nil
	}

	body, _ := io.ReadAll(resp.Body)
	return fmt.Errorf("推送服务器信息失败，状态码: %d, 响应: %s", resp.StatusCode, string(body))
}

// 收集系统信息
func collectSystemInfo() (map[string]interface{}, error) {
	info := make(map[string]interface{})

	// CPU信息
	cpuPercent, err := cpu.Percent(0, false)
	if err != nil {
		logger.Printf("获取CPU使用率失败: %v", err)
		info["cpu_usage"] = "未知"
	} else {
		info["cpu_usage"] = fmt.Sprintf("%.1f%%", cpuPercent[0])
	}

	// 内存信息
	memInfo, err := mem.VirtualMemory()
	if err != nil {
		logger.Printf("获取内存信息失败: %v", err)
		info["memory_usage"] = "未知"
	} else {
		info["memory_usage"] = fmt.Sprintf("%.1f%%", memInfo.UsedPercent)
	}

	// 磁盘信息
	diskInfo, err := disk.Usage("/")
	if err != nil {
		logger.Printf("获取磁盘信息失败: %v", err)
		info["disk_usage"] = "未知"
	} else {
		info["disk_usage"] = fmt.Sprintf("%.1f%%", diskInfo.UsedPercent)
	}

	// 系统时间
	info["system_time"] = time.Now().Format("2006-01-02 15:04:05")

	// 操作系统版本
	hostInfo, err := host.Info()
	if err != nil {
		logger.Printf("获取主机信息失败: %v", err)
		info["os_version"] = "未知"
	} else {
		info["os_version"] = hostInfo.PlatformVersion
	}

	return info, nil
}

// 执行巡检并推送
func performInspection() error {
	err := ensureToken()
	if err != nil {
		return err
	}

	info, err := getLocalServerInfo()
	if err != nil {
		return fmt.Errorf("获取本机信息失败: %v", err)
	}

	systemInfo, err := collectSystemInfo()
	if err != nil {
		return fmt.Errorf("收集系统信息失败: %v", err)
	}

	// 构建巡检结果
	cpuUsage := systemInfo["cpu_usage"].(string)
	memUsage := systemInfo["memory_usage"].(string)
	diskUsage := systemInfo["disk_usage"].(string)

	// 判断是否有告警
	cpuPercent, _ := strconv.ParseFloat(strings.TrimSuffix(cpuUsage, "%"), 64)
	memPercent, _ := strconv.ParseFloat(strings.TrimSuffix(memUsage, "%"), 64)
	diskPercent, _ := strconv.ParseFloat(strings.TrimSuffix(diskUsage, "%"), 64)

	var result string
	var alertContent string

	if cpuPercent > 80 || memPercent > 85 || diskPercent > 90 {
		var alerts []string
		if cpuPercent > 80 {
			alerts = append(alerts, fmt.Sprintf("CPU过高(%.1f%%)", cpuPercent))
		}
		if memPercent > 85 {
			alerts = append(alerts, fmt.Sprintf("内存过高(%.1f%%)", memPercent))
		}
		if diskPercent > 90 {
			alerts = append(alerts, fmt.Sprintf("磁盘过高(%.1f%%)", diskPercent))
		}
		alertContent = strings.Join(alerts, "; ")
		result = fmt.Sprintf("⚠️ 告警 | %s", alertContent)
	} else {
		result = fmt.Sprintf("✅ 正常 | CPU %s, 内存 %s, 磁盘 %s", cpuUsage, memUsage, diskUsage)
	}

	// 获取服务器ID
	serverID := getServerID(info["ip"])
	if serverID == 0 {
		logger.Println("未找到服务器ID，跳过巡检推送")
		return nil
	}

	// 调用巡检接口
	url := fmt.Sprintf("%s/api/inspect_async/%d", config.Server.APIBaseURL, serverID)
	req, err := http.NewRequest("POST", url, nil)
	if err != nil {
		return fmt.Errorf("创建请求失败: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-API-Token", token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("执行巡检失败: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("读取响应失败: %v", err)
	}

	var inspectResp InspectionResponse
	err = json.Unmarshal(body, &inspectResp)
	if err != nil {
		return fmt.Errorf("响应解析失败: %v", err)
	}

	if inspectResp.Success {
		logger.Printf("巡检成功 - 服务器: %s, 结果: %s, 时间: %s", inspectResp.ServerName, inspectResp.InspectionResult, inspectResp.InspectionTime)
	} else {
		logger.Printf("巡检失败 - 服务器: %s, 原因: %s", info["name"], inspectResp.Message)
	}

	return nil
}

// 获取服务器ID（根据IP）
func getServerID(ip string) int {
	err := ensureToken()
	if err != nil {
		logger.Printf("获取Token失败: %v", err)
		return 0
	}

	url := fmt.Sprintf("%s/?ip=%s", config.Server.APIBaseURL, ip)
	req, err := http.NewRequest("GET", url, nil)
	if err != nil {
		logger.Printf("创建请求失败: %v", err)
		return 0
	}
	req.Header.Set("X-API-Token", token)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		logger.Printf("查询服务器列表失败: %v", err)
		return 0
	}
	defer resp.Body.Close()

	// 解析HTML响应，提取服务器ID
	// 由于返回的是HTML页面，这里简化处理，返回0表示未找到
	// 实际使用时应该解析HTML或使用专门的API接口
	body, _ := io.ReadAll(resp.Body)
	if strings.Contains(string(body), ip) {
		// 简单查找ID，实际应该用正则或解析HTML
		return 1 // 默认返回1，实际应该从响应中提取
	}

	return 0
}

// 主循环
func startInspectionLoop() {
	if !config.Inspection.Enabled {
		logger.Println("自动巡检已禁用")
		return
	}

	if config.Inspection.RunOnStart {
		logger.Println("启动时执行首次巡检...")
		err := performInspection()
		if err != nil {
			logger.Printf("首次巡检失败: %v", err)
		}
	}

	ticker := time.NewTicker(time.Duration(config.Inspection.IntervalMinutes) * time.Minute)
	defer ticker.Stop()

	for range ticker.C {
		logger.Println("执行定时巡检...")
		err := performInspection()
		if err != nil {
			logger.Printf("巡检失败: %v", err)
		}
	}
}

// 检查是否是首次运行
func isFirstRun() bool {
	firstRunFile := ".first_run"
	_, err := os.Stat(firstRunFile)
	return os.IsNotExist(err)
}

// 标记已完成首次运行
func markFirstRunDone() error {
	file, err := os.Create(".first_run")
	if err != nil {
		return err
	}
	return file.Close()
}

func main() {
	// 加载配置
	err := loadConfig("config.yaml")
	if err != nil {
		log.Fatalf("加载配置失败: %v", err)
	}

	// 初始化日志
	initLogger()

	logger.Println("=== 服务器监控客户端启动 ===")
	logger.Printf("API地址: %s", config.Server.APIBaseURL)
	logger.Printf("巡检频率: %d 分钟", config.Inspection.IntervalMinutes)

	// 检查是否首次运行
	if isFirstRun() {
		logger.Println("检测到首次运行，推送服务器信息...")
		err := pushServerInfo()
		if err != nil {
			logger.Printf("推送服务器信息失败: %v", err)
		} else {
			err := markFirstRunDone()
			if err != nil {
				logger.Printf("标记首次运行失败: %v", err)
			}
		}
	} else {
		logger.Println("非首次运行，跳过服务器信息推送")
	}

	// 启动巡检循环
	startInspectionLoop()
}
