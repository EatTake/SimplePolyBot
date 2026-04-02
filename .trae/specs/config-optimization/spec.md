# 交易策略参数配置优化 Spec

## Why

当前 SimplePolyBot 的配置系统虽然功能完整，但对非技术用户不够友好。需要全面优化参数配置的易用性，降低使用门槛，使非技术用户也能轻松配置和执行交易策略。

## What Changes

### 核心优化内容
1. **参数梳理与分类**: 全面整理所有可配置参数，按模块和用途分类
2. **交互式配置向导**: 创建命令行交互式配置工具，引导用户完成配置
3. **增强验证机制**: 实现全面的参数输入验证，提供明确的修正建议
4. **配置方案管理**: 支持保存、加载、切换多个配置方案（如保守型、激进型）
5. **智能文档生成**: 自动生成参数说明文档，包含用途、范围、默认值
6. **友好错误提示**: 优化错误信息格式，包含问题描述、当前值、建议修正

### 新增文件
- `shared/config_wizard.py` - 交互式配置向导
- `shared/config_validator.py` - 增强验证器（含建议生成）
- `shared/config_presets.py` - 预设配置方案管理器
- `config/presets/` - 预设配置方案目录
- `docs/configuration_guide.md` - 用户配置指南

### 修改文件
- `shared/config.py` - 扩展配置管理功能
- `config/settings.yaml` - 增强注释和分组
- `.env.example` - 补充环境变量说明

---

## Impact

### Affected Specs
- 配置管理系统全面升级
- 所有模块的初始化流程（支持新的配置方式）

### Affected Code
- `shared/config.py` - 核心配置管理
- 所有模块的 main.py - 初始化入口
- `scripts/` - 启动脚本

---

## ADDED Requirements

### Requirement: 参数全面梳理与分类

系统 SHALL 提供完整的参数清单，按以下维度分类：

#### Scenario: 按模块分类
- **WHEN** 用户查看参数列表
- **THEN** 系统显示按模块分组的参数：策略参数、风险控制、订单管理、连接配置等

#### Scenario: 按重要性分类
- **WHEN** 用户筛选参数
- **THEN** 系统区分核心参数（必填）和高级参数（可选）

#### Scenario: 按安全级别分类
- **WHEN** 用户编辑敏感参数
- **THEN** 系统标记 API 密钥、私钥等为敏感参数，显示警告

---

### Requirement: 交互式配置向导

系统 SHALL 提供 CLI 交互式配置工具：

#### Scenario: 首次配置引导
- **WHEN** 用户首次运行配置向导 (`python -m shared.config_wizard`)
- **THEN** 系统逐步引导用户填写：
  1. 基本设置（环境选择、日志级别）
  2. 连接配置（Redis、API 地址）
  3. 凭证配置（私钥、API Key）- 敏感信息特殊处理
  4. 策略参数（Base Cushion、Alpha 等）
  5. 风险管理参数
  6. 保存并验证配置

#### Scenario: 快速配置模式
- **WHEN** 用户选择"快速配置"
- **THEN** 系统仅询问核心参数，其余使用默认值

#### Scenario: 专家模式
- **WHEN** 用户选择"专家模式"
- **THEN** 系统展示所有参数供详细配置

---

### Requirement: 增强参数验证

系统 SHALL 实现智能参数验证：

#### Scenario: 范围验证
- **WHEN** 用户输入超出范围的值（如 alpha=1.5）
- **THEN** 系统提示：
  ```
  ❌ alpha 值无效
     当前值: 1.5
     有效范围: 0.0 - 1.0
     建议值: 0.3 (保守) / 0.5 (平衡) / 0.7 (激进)
  ```

#### Scenario: 类型验证
- **WHEN** 用户输入类型错误的值（如 port="abc"）
- **THEN** 系统提示类型要求并提供示例

#### Scenario: 依赖关系验证
- **WHEN** 用户设置的参数组合存在冲突
- **THEN** 系统检测依赖关系并提示：
  ```
  ⚠️ 参数冲突检测
     min_order_size (10) > max_order_size (5)
     建议: 将 max_order_size 设置为至少 10
  ```

#### Scenario: 必填项检查
- **WHEN** 用户未填写必填参数
- **THEN** 系统明确标识缺失的必填项并阻止继续

---

### Requirement: 预设配置方案

系统 SHALL 提供预设配置方案：

#### Scenario: 查看可用方案
- **WHEN** 用户运行 `python -m shared.config_presets list`
- **THEN** 系统显示：
  ```
  可用配置方案:
  📋 conservative   - 保守型 (低风险低收益)
  📋 balanced      - 平衡型 (中等风险收益) [默认]
  📋 aggressive    - 激进型 (高风险高收益)
  📋 custom        - 自定义方案
  ```

#### Scenario: 应用预设方案
- **WHEN** 用户运行 `python -m shared.config_presets apply balanced`
- **THEN** 系统加载对应方案并更新 settings.yaml

#### Scenario: 创建自定义方案
- **WHEN** 用户运行 `python -m shared.config_presets save my_strategy`
- **THEN** 系统将当前配置保存为可复用的方案

#### Scenario: 对比方案差异
- **WHEN** 用户运行 `python -m shared.config_presets diff conservative aggressive`
- **THEN** 系统显示两个方案的参数对比表

---

### Requirement: 配置文档自动生成

系统 SHALL 自动生成参数说明文档：

#### Scenario: 生成 Markdown 文档
- **WHEN** 用户运行 `python -m shared.config_docs generate`
- **THEN** 系统生成 `docs/configuration_guide.md`，包含：
  - 参数名称和路径
  - 用途说明（中文）
  - 数据类型
  - 取值范围/可选值
  - 默认值
  - 示例值
  - 关联参数说明
  - 修改影响说明

#### Scenario: 生成 JSON Schema
- **WHEN** 用户运行 `python -m shared.config_docs schema`
- **THEN** 系统生成 `config/settings.schema.json` 用于 IDE 自动补全

---

### Requirement: 友好错误提示

系统 SHALL 优化所有配置相关错误信息：

#### Scenario: 格式化错误输出
- **WHEN** 配置加载或验证失败
- **THEN** 错误信息格式统一为：
  ```
  ╔══════════════════════════════════════╗
  ║  配置错误                           ║
  ╠══════════════════════════════════════╣
  ║ 位置: strategy.alpha (第12行)       ║
  ║  问题: 值超出有效范围               ║
  ║  当前值: 1.5                        ║
  ║  有效范围: 0.0 - 1.0                ║
  ║                                      ║
  ║  💡 建议:                            ║
  ║  - 使用保守值: 0.3                  ║
  ║  - 使用默认值: 0.5                  ║
  ║  - 使用激进值: 0.7                  ║
  ╚══════════════════════════════════════╝
  ```

#### Scenario: 多错误汇总
- **WHEN** 存在多个配置错误
- **THEN** 系统汇总所有错误，一次性展示，避免反复修改

#### Scenario: 修复指引
- **WHEN** 出现配置错误
- **THEN** 系统提供具体的修复步骤和命令示例

---

## MODIFIED Requirements

### Requirement: 配置管理器扩展

现有 Config 类 SHALL 增加以下功能：

```python
class Config:
    # ... 现有方法 ...
    
    def get_parameter_info(self, key: str) -> ParameterInfo:
        """获取参数详细信息（类型、范围、说明等）"""
    
    def get_all_parameters(self, category: str | None = None) -> list[ParameterInfo]:
        """获取参数列表，可按类别过滤"""
    
    def export_preset(self, name: str, path: Path | None = None) -> None:
        """导出当前配置为预设方案"""
    
    def import_preset(self, name: str, path: Path | None = None) -> None:
        """导入预设方案"""
    
    def validate_with_suggestions(self) -> ValidationResult:
        """带建议的验证结果"""
    
    def generate_docs(self, format: str = "markdown") -> str:
        """生成参数文档"""
```

---

## REMOVED Requirements

无移除的需求。

---

## 实施计划

### Phase 1: 参数梳理与文档基础（Task 1-2）
1. 创建 ParameterInfo 数据类定义参数元数据
2. 建立完整参数注册表
3. 实现 get_parameter_info() 和 get_all_parameters()

### Phase 2: 增强验证机制（Task 3-4）
1. 重构 ConfigValidator 类
2. 实现范围/类型/依赖/必填验证
3. 实现建议生成算法
4. 优化错误消息格式化

### Phase 3: 交互式配置工具（Task 5-7）
1. 实现配置向导 CLI 工具
2. 实现快速/专家模式切换
3. 实现敏感信息特殊处理

### Phase 4: 预设方案管理（Task 8-9）
1. 创建预设方案文件
2. 实现预设方案 CRUD 操作
3. 实现方案对比功能

### Phase 5: 文档生成与集成（Task 10-11）
1. 实现文档自动生成
2. 生成 JSON Schema
3. 更新 .env.example 和 README

---

## 成功标准

1. ✅ 所有参数可通过 `get_all_parameters()` 获取完整元数据
2. ✅ 配置向导可引导非技术用户完成首次配置（< 3分钟）
3. ✅ 验证错误信息包含问题、范围、建议三要素
4. ✅ 至少提供 3 个预设方案（保守/平衡/激进）
5. ✅ 自动生成的配置指南涵盖所有参数
6. ✅ 错误提示格式统一美观，易于理解
7. ✅ 所有新功能有对应的单元测试
8. ✅ 现有测试全部通过
