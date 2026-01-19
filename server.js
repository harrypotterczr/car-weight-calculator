const express = require('express');
const fs = require('fs');
const path = require('path');
const { PythonShell } = require('python-shell');
const { spawn } = require('child_process');

const app = express();
const PORT = 3000;

// 中间件
app.use(express.json());
app.use(express.static('.'));

app.get('/car_weight_calculator', (req, res) => {
    res.sendFile(path.join(__dirname, 'car_weight_calculator.html'));
});

app.get('/component_weight_calculator', (req, res) => {
    res.sendFile(path.join(__dirname, 'component_weight_calculator.html'));
});
// 读取组件数据
const componentsData = JSON.parse(fs.readFileSync('formulas_optimized.json', 'utf8'));

// 获取所有组件图号的API
app.get('/api/components', (req, res) => {
    const componentList = componentsData.map(component => ({
        component_drawing_no: component.component_drawing_no,
        model_type: component.model_type,
        r2_score: component.r2_score
    }));
    res.json(componentList);
});

// 获取特定组件信息的API
app.get('/api/component/:drawingNo', (req, res) => {
    let drawingNo = req.params.drawingNo;
    
    console.log(`搜索组件: "${drawingNo}"`);
    
    // 处理特殊字符编码问题
    // 将空格转换为换行符，以匹配JSON中的实际值
    const processedDrawingNo = drawingNo.replace(/ /g, '\n');
    
    console.log(`处理后的组件名: "${processedDrawingNo}"`);
    
    // 多种匹配策略
    let component = null;
    
    // 策略1: 精确匹配处理后的值
    component = componentsData.find(c => c.component_drawing_no === processedDrawingNo);
    
    // 策略2: 精确匹配原始值
    if (!component) {
        component = componentsData.find(c => c.component_drawing_no === drawingNo);
    }
    
    // 策略3: 模糊匹配 - 将JSON中的换行符替换为空格进行比较
    if (!component) {
        component = componentsData.find(c => 
            c.component_drawing_no.replace(/\n/g, ' ') === drawingNo
        );
    }
    
    // 策略4: 模糊匹配 - 去除所有空白字符进行比较
    if (!component) {
        const normalizedInput = drawingNo.replace(/\s/g, '');
        component = componentsData.find(c => 
            c.component_drawing_no.replace(/\s/g, '') === normalizedInput
        );
    }
    
    // 策略5: 部分匹配 - 检查是否包含组件号的主要部分
    if (!component) {
        // 提取主要部分进行匹配
        const mainPart = drawingNo.replace(/\s/g, '').substring(0, 8);
        component = componentsData.find(c => 
            c.component_drawing_no.replace(/\s/g, '').includes(mainPart)
        );
    }
    
    if (!component) {
        console.log('组件未找到');
        return res.status(404).json({ error: 'Component not found' });
    }
    
    console.log(`找到组件: ${component.component_drawing_no}`);
    res.json(component);
});

// 计算重量的API
app.post('/api/calculate', async (req, res) => {
    let { component_drawing_no, parameters } = req.body;
    
    // 处理特殊字符编码问题
    // 将空格转换为换行符，以匹配JSON中的实际值
    component_drawing_no = component_drawing_no.replace(/ /g, '\n');
    
    // 查找组件
    const component = componentsData.find(c => c.component_drawing_no === component_drawing_no);
    
    if (!component) {
        return res.status(404).json({ error: 'Component not found' });
    }
    
    // 验证参数
    if (!parameters) {
        return res.status(400).json({ error: 'Parameters are required' });
    }
    
    // 检查是否所有必需的参数都已提供
    const missingParams = component.parameters.filter(param => !(param in parameters));
    if (missingParams.length > 0) {
        return res.status(400).json({ error: `Missing parameters: ${missingParams.join(', ')}` });
    }
    
    try {
        let weight;
        
        if (component.model_type === 'random_forest') {
            // 对于随机森林模型，使用实际的模型进行计算
            weight = await calculateUsingRandomForest(component_drawing_no, parameters);
        } else {
            // 使用公式计算
            weight = calculateUsingFormula(component.formula, parameters);
        }
        
        res.json({
            component_drawing_no,
            weight: parseFloat(weight.toFixed(2)),
            model_type: component.model_type,
            r2_score: component.r2_score
        });
    } catch (error) {
        res.status(500).json({ error: 'Calculation error: ' + error.message });
    }
});

// 使用公式计算重量
function calculateUsingFormula(formula, parameters) {
    try {
        // 移除 "unit_weight = " 前缀
        let expression = formula.replace('unit_weight = ', '');
        
        // 先处理乘方运算（支持中英文参数）
        expression = expression.replace(/([a-zA-Z\u4e00-\u9fa5]+)\^(\d+)/g, 'Math.pow($1, $2)');
        
        // 处理参数之间的乘法（如 CA CH 变成 CA*CH）
        expression = expression.replace(/([a-zA-Z\u4e00-\u9fa5]+)\s+([a-zA-Z\u4e00-\u9fa5]+)/g, '$1*$2');
        
        // 替换参数值 - 先替换多字符参数，再替换单字符参数，避免部分匹配问题
        // 按参数名长度降序排列，确保长参数名先被替换
        const sortedParams = Object.entries(parameters).sort((a, b) => 
            b[0].length - a[0].length
        );
        
        for (const [param, value] of sortedParams) {
            // 对于中文参数，使用更精确的匹配方式
            if (/[\u4e00-\u9fa5]/.test(param)) {
                // 中文参数直接替换，不使用单词边界
                const regex = new RegExp(param.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g');
                expression = expression.replace(regex, value.toString());
            } else {
                // 英文参数使用单词边界确保完整匹配
                const escapedParam = param.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                const regex = new RegExp('\\b' + escapedParam + '\\b', 'g');
                expression = expression.replace(regex, value.toString());
            }
        }
        
        // 处理剩余的空格（最后处理）
        expression = expression.replace(/\s+/g, '');
        
        console.log('计算表达式:', expression);
        
        // 计算表达式
        const result = eval(expression);
        return result;
    } catch (error) {
        throw new Error('Formula calculation error: ' + error.message);
    }
}

// 随机森林模型计算
function calculateUsingRandomForest(component_drawing_no, parameters) {
    return new Promise((resolve, reject) => {
        console.log(`开始计算随机森林模型: ${component_drawing_no}`);
        console.log(`参数:`, parameters);
        
        // 构造模型文件路径
        const modelPath = path.join(__dirname, 'Random Forest Models', `${component_drawing_no}_rf_model.pkl`);
        console.log(`模型文件路径: ${modelPath}`);
        
        // 检查模型文件是否存在
        if (!fs.existsSync(modelPath)) {
            console.error(`模型文件不存在: ${modelPath}`);
            reject(new Error(`Model file not found: ${modelPath}`));
            return;
        }
        
        // 将参数转换为JSON字符串
        const parametersJson = JSON.stringify(parameters);
        console.log(`参数JSON: ${parametersJson}`);
        
        // 使用spawn直接调用Python脚本
        console.log(`使用spawn调用Python脚本: predict_rf.py`);
        const pythonProcess = spawn('python', ['predict_rf.py', modelPath, parametersJson], {
            cwd: __dirname
        });
        
        let stdout = '';
        let stderr = '';
        
        pythonProcess.stdout.on('data', (data) => {
            stdout += data.toString();
            console.log(`Python脚本stdout: ${data}`);
        });
        
        pythonProcess.stderr.on('data', (data) => {
            stderr += data.toString();
            console.error(`Python脚本stderr: ${data}`);
        });
        
        pythonProcess.on('close', (code) => {
            console.log(`Python脚本退出，退出码: ${code}`);
            console.log(`stdout: ${stdout}`);
            console.log(`stderr: ${stderr}`);
            
            if (code !== 0) {
                reject(new Error(`Python脚本执行失败，退出码: ${code}, 错误: ${stderr}`));
                return;
            }
            
            // 解析结果
            const lines = stdout.trim().split('\n');
            if (lines.length > 0) {
                const prediction = parseFloat(lines[0]);
                console.log(`预测结果: ${prediction}`);
                if (isNaN(prediction)) {
                    console.error(`无效的预测结果: ${lines[0]}`);
                    reject(new Error('Invalid prediction result'));
                    return;
                }
                resolve(prediction);
            } else {
                console.error(`没有返回预测结果`);
                reject(new Error('No prediction result returned'));
            }
        });
        
        pythonProcess.on('error', (error) => {
            console.error(`启动Python脚本失败: ${error}`);
            reject(new Error(`Failed to start Python script: ${error.message}`));
        });
    });
}

// 归档轿厢重量数据的API
app.post('/api/archive', (req, res) => {
    try {
        const data = req.body;
        const filePath = path.join(__dirname, '轿厢重量汇总.json');
        let currentData = [];
        
        if (fs.existsSync(filePath)) {
            try {
                const fileContent = fs.readFileSync(filePath, 'utf8');
                if (fileContent.trim()) {
                    const parsed = JSON.parse(fileContent);
                    if (Array.isArray(parsed)) {
                        currentData = parsed;
                    } else {
                        currentData = [parsed];
                    }
                }
            } catch (e) {
                console.error('Error reading archive file:', e);
                // If error reading, start fresh or backup? For now, start fresh but maybe log warning
            }
        }
        
        // Add timestamp if not present
        if (!data.timestamp) {
            data.timestamp = new Date().toISOString();
        }
        
        currentData.push(data);
        
        fs.writeFileSync(filePath, JSON.stringify(currentData, null, 2), 'utf8');
        console.log('Data archived successfully');
        res.json({ success: true });
    } catch (error) {
        console.error('Archive error:', error);
        res.status(500).json({ error: 'Failed to archive data: ' + error.message });
    }
});

// 启动服务器
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
