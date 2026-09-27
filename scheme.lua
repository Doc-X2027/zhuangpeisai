--[[
    脚本功能：AUBO机械臂TCP客户端通信脚本
    功能描述：
    1. 连接TCP服务器
    2. 持续监听服务器发送的信息
    3. 收到request：结束脚本，scheme变量被赋值为request
    ...
    4. 未收到信息或连接异常：继续监听，scheme变量保持为0
    注：脚本使用LuaSocket库
]]

local socket = require("socket")

-- ==================== parameters ====================
local SERVER_IP = "192.168.34.99"   -- VMware VMnet8 host address running app.py
local SERVER_PORT = 8888            -- app.py TCP listener
local REQUEST = "planning"           -- app.py command: identify, planning, or auto
local TIMEOUT = 600                  -- model request may take several minutes
local RECONNECT_DELAY = 2            -- 断线重连延迟（秒）
-- ================================================

-- scheme变量初始值为0
scheme = 0
textmsg("脚本启动，scheme: 0")

-- 持续监听标志
local running = true

-- 定义服务器连接与监听函数
function listen_server()
    local client = nil
    local connected = false
    
    client = socket.tcp()
    client:settimeout(TIMEOUT)
    
    -- textmsg("尝试连接服务器 " .. SERVER_IP .. ":" .. SERVER_PORT)
    local success, err = client:connect(SERVER_IP, SERVER_PORT)
    
    if success then
        textmsg("连接服务器成功")
        connected = true
        local sent, send_err = client:send(REQUEST)
        if not sent then
            textmsg("发送命令失败: " .. tostring(send_err))
            client:close()
            return
        end
    --else
    --    textmsg("连接失败: " .. tostring(err) .. "，" .. RECONNECT_DELAY .. "秒后重试")
    --    client:close()
    --    client = nil
    --    socket.sleep(RECONNECT_DELAY)
    --    goto continue
    end

    while running do
        -- 设置接收超时，实现非阻塞持续监听
        client:settimeout(TIMEOUT)
        
        -- app.py sends a raw response and closes the socket; it does not append a newline.
        local response, err = client:receive("*a")
        
        if response then
            textmsg("收到服务器消息: " .. response)
            scheme = response
            textmsg("接收到" .. scheme .. "指令，scheme: " .. scheme)
            running = false
            break
        elseif err == "timeout" then
            -- 超时未收到数据，继续循环（scheme保持0）
            -- 可在此添加心跳或状态输出（可选）
            textmsg("监听中...")
        else
            -- 连接异常中断
            textmsg("接收错误: " .. tostring(err) .. "，准备重连")
            client:close()
            client = nil
            connected = false
            socket.sleep(RECONNECT_DELAY)
        end
        ::continue::
    end
    
    -- 清理连接
    if client then
        client:close()
    end
end

-- ==================== main ====================
listen_server()
textmsg("执行方案" .. tostring(scheme))
