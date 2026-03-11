# 电梯轿厢重量计算器 (Elevator Car Weight Calculator)

这是一个基于 Web 的应用程序，用于计算电梯轿厢组件及整梯系统的重量。该工具结合了传统的数学公式计算和机器学习（随机森林）模型，以提供精确的重量估算。

## 主要功能

- **轿厢总重计算**: 
  - 根据轿厢尺寸（CA 宽、CB 深、CH 高）、开门宽度（JJ）和材质规格计算总重。
  - 支持多种轿壁类型（19mm、25mm、30mm）及不同材质。
  - **自动计算**: 内置逻辑自动推导前壁和侧柱的重量。
  - **贯通门支持**: 可切换贯通/非贯通模式，自动调整后壁与侧壁数量。

- **门机重量数据库**:
  - 内置主流门机厂家的重量数据，包括：
    - 佛马特 (Fermator)
    - 易升 (E-Sheng)
    - 威特 (Wittur)
    - GAL
  - **智能匹配**: 根据厂家、开门方式（中分/旁开）、JJ 和地坎宽度（SW）自动匹配重量。
  - **动态交互**: 选择厂家后，SW 输入框会自动变为对应规格的下拉菜单。

- **组件重量计算器**:
  - 独立的组件计算界面。
  - 基于 `formulas_optimized.json` 中定义的公式进行精确计算。
  - 对于复杂组件，集成 Python 随机森林模型 (`.pkl`) 进行预测。

- **导出与归档**:
  - **服务端 PDF 生成**: 点击“导出 PDF”按钮，服务端自动生成高清 PDF 报告。
    - 自动以“项目号+轿厢重量”命名文件。
    - 完美适配打印样式，自动去除深色背景，确保打印输出清晰整洁。
    - 解决浏览器原生打印的输入框截断和样式兼容性问题。
  - **数据归档**: 支持将计算数据归档保存为 JSON 格式。

## 技术栈

- **前端**: HTML5, CSS3, JavaScript (原生)
- **后端**: Node.js, Express.js, Puppeteer-core (PDF 生成)
- **机器学习**: Python (scikit-learn), Random Forest Regressor

## 环境要求

- **Node.js**: v14.0.0 或更高版本
- **Python**: 3.8 或更高版本
- **Chrome 浏览器**: 用于 PDF 生成（服务端自动调用本机 Chrome/Edge）
- **Python 依赖库**:
  ```bash
  pip install scikit-learn pandas numpy joblib
  ```

## 安装步骤

1. 克隆仓库:
   ```bash
   git clone https://github.com/harrypotterczr/car-weight-calculator.git
   cd car-weight-calculator
   ```

2. 安装 Node.js 依赖:
   ```bash
   npm install
   ```

3. 确保已安装 Python 及相关库。

## 使用说明

1. **一键启动 (推荐)**:
   双击运行 `start_car_weight_calculator.bat` 脚本。
   - 自动关闭旧的服务进程。
   - 后台静默启动服务器（无黑框干扰）。
   - 自动打开默认浏览器访问应用。

2. 手动启动:
   ```bash
   npm start
   ```
   或者使用开发模式（自动重载）:
   ```bash
   npm run dev
   ```

2. 在浏览器中访问:
   - **轿厢重量计算器 (本地)**: [http://localhost:3000/](http://localhost:3000/)
   - **组件重量计算器 (本地)**: [http://localhost:3000/component_weight_calculator](http://localhost:3000/component_weight_calculator)
   - **在线预览 (GitHub Pages)**: [https://harrypotterczr.github.io/car-weight-calculator](https://harrypotterczr.github.io/car-weight-calculator)

## 文件结构

- `index.html`: 轿厢重量计算主界面 (原 car_weight_calculator.html)。
- `server.js`: Node.js 后端服务器。
- `formulas_optimized.json`: 包含计算公式和参数定义的配置文件。
- `Random Forest Models/`: 存放预训练的机器学习模型文件 (`.pkl`)。
- `predict_rf.py`: 用于加载模型并进行预测的 Python 脚本。
- `轿厢重量汇总.json`: 用于存储归档数据的 JSON 文件。

## 许可证

MIT
