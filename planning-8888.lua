function split(str, delimiter)  --声明字符分割函数
	if str==nil or str=='' or delimiter==nil then
		return nil
 	end

 	local result = {}
 	for match in (str..delimiter):gmatch("(.-)"..delimiter) do
 		table.insert(result, match)
	end
	return result
end

local socket = require("socket.core")
local tcp = socket.tcp()
local host = '192.168.34.99' --服务端IP地址
local port = 8888 -- app.py 的 read/任务指令 TCP 端口；6000 是拍照端口
local connected, connect_err = tcp:connect(host, port)
if not connected then
    textmsg("连接 App 失败: " .. tostring(connect_err))
    tcp:close()
    return
end

tcp:settimeout(120)

str1 = ""
textmsg("ok1")
    --发送给服务端字符串
    tcp:send("read")
    textmsg("ok2")
    -- App 发送原始任务指令后会关闭连接，不附加换行符。
    -- "*a" 会读到连接关闭；关闭前的数据可能在 partial 中。
    local received, status, partial = tcp:receive("*a")
    str1 = received or partial or ""
    if status == "timeout" and str1 == "" then
        textmsg("接收超时")
    elseif status and status ~= "closed" and str1 == "" then
        textmsg("接收错误: " .. tostring(status))
    end
    textmsg("ok3")
if (str1 ~= "") then
    textmsg("ok4")
    textmsg("receive: "..str1)--打印recv
    table1 = split(str1, ";")
    textmsg("ok5")
    obj1 = table1[1]
    tgt1 = table1[2]
    obj2 = table1[3]
    tgt2 = table1[4]
    obj3 = table1[5]
    tgt3 = table1[6]
    obj4 = table1[7]
    tgt4 = table1[8]
    obj5 = table1[9]
    tgt5 = table1[10]
    obj6 = table1[11]
    tgt6 = table1[12]
    obj7 = table1[13]
    tgt7 = table1[14]
    textmsg("ok6")
end
tcp:close()
