# 青程 Agent 真实场景 Benchmark 报告

## 总体得分

- 总分：620/648（95.7%）
- 评测轮数：36
- Goal Accuracy：77.8%
- Retrieval Precision：94.4%
- 官方来源占比：100.0%
- 平均响应时间：18278 ms
- P0：3；P1：8

## Case 明细

### C01 / Turn 1：普通会话

- 输入：你好
- Goal：CONVERSATIONAL（期望 CONVERSATIONAL）
- 节点：resolve_goal → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：你好！我是青程 Agent，可以帮你了解高校毕业生就业创业政策、办理流程或资格判断。
- 得分：18/18
- 严重级别：无
- 问题：无

### C02 / Turn 1：普通会话

- 输入：谢谢
- Goal：CONVERSATIONAL（期望 CONVERSATIONAL）
- 节点：resolve_goal → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：不客气。需要了解政策、办理流程或资格判断时，随时告诉我。
- 得分：18/18
- 严重级别：无
- 问题：无

### C03 / Turn 1：普通会话

- 输入：你是谁
- Goal：CONVERSATIONAL（期望 CONVERSATIONAL）
- 节点：resolve_goal → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：我是青程 Agent，主要协助高校毕业生了解就业创业政策、办理流程和资格判断。
- 得分：18/18
- 严重级别：无
- 问题：无

### C04 / Turn 1：普通会话

- 输入：我都没告诉你我的情况，你怎么知道的
- Goal：CONVERSATIONAL（期望 CONVERSATIONAL）
- 节点：resolve_goal → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：你说得对。在你没有明确提供个人情况时，我不应该作个性化推断；目前我没有你的个人画像。
- 得分：18/18
- 严重级别：无
- 问题：无

### C05 / Turn 1：JOB_SEARCH

- 输入：我是2026届本科生，现在没工作，只想找工作
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：如果你的目标是尽快找工作，当前可优先关注求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴。
- 得分：18/18
- 严重级别：无
- 问题：无

### C06 / Turn 1：JOB_SEARCH

- 输入：我快毕业了，不知道去哪找工作
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。
- 得分：18/18
- 严重级别：无
- 问题：无

### C07 / Turn 1：JOB_SEARCH

- 输入：我不想创业，只想就业
- Goal：POLICY_DISCOVERY（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-startup-one-time-2023, suzhou-startup-social-2021
- 追问：无
- 回复：根据你目前提供的信息，可先了解：求职创业补贴（2026届毕业生申领通知）、一次性创业补贴、创业社会保险补贴。

相关官方公开信息：
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/b3b080ceb9804595b9a6b17196e587c6.shtml
发布时间：2026-09-18
该通知尚未完成结构化核验，不能据此自动判断个人资格。
致2026届高校毕业生的一封信 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发布时间：2026-08-13
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202603/d0dfcee897fb4cb398b47ba9b9084a72.shtml
发布时间：2026-03-12
该通知尚未完成结构化核验，不能据此自动判断个人资格。
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/wdk.shtml
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：14/18
- 严重级别：P0, P1
- 问题：目标误判：期望 JOB_SEARCH，实际 POLICY_DISCOVERY；无画像时出现个性化断言

### C08 / Turn 1：JOB_SEARCH

- 输入：苏州最近有什么适合毕业生的就业服务
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：如果你的目标是尽快找工作，当前可优先关注就业见习、求职创业补贴（2026届毕业生申领通知）。

相关官方公开信息：
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/ad1909e2cf2d49c0bcba0f40f70e1801.shtml
发布时间：2026-09-02
该通知尚未完成结构化核验，不能据此自动判断个人资格。
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
致2026届高校毕业生的一封信 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发布时间：2026-08-13
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C09 / Turn 1：POLICY_DISCOVERY

- 输入：苏州毕业生现在有什么就业支持
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：根据你目前提供的信息，可先了解：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴、一次性创业补贴。

相关官方公开信息：
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/ad1909e2cf2d49c0bcba0f40f70e1801.shtml
发布时间：2026-09-02
该通知尚未完成结构化核验，不能据此自动判断个人资格。
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
致2026届高校毕业生的一封信 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发布时间：2026-08-13
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：16/18
- 严重级别：P0
- 问题：无画像时出现个性化断言

### C10 / Turn 1：POLICY_DISCOVERY

- 输入：我今年毕业，有什么政策可以看看
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：根据你目前提供的信息，可先了解：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴。
- 得分：18/18
- 严重级别：无
- 问题：无

### C11 / Turn 1：POLICY_DISCOVERY

- 输入：未就业毕业生有哪些支持
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。

相关官方公开信息：
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/ad1909e2cf2d49c0bcba0f40f70e1801.shtml
发布时间：2026-09-02
该通知尚未完成结构化核验，不能据此自动判断个人资格。
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
致2026届高校毕业生的一封信 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发布时间：2026-08-13
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C12 / Turn 1：POLICY_DISCOVERY

- 输入：创业的话有什么政策
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：根据苏州市现行政策，高校毕业生创业主要有以下两项补贴支持，供您参考：

---

**一、创业社会保险补贴**

- **适用对象**：毕业5年内的高校毕业生
- **基本条件**：
  - 依法连续缴纳社会保险满1年及以上
  - 申请时市场主体登记注册在3年以内
- **补贴标准**：每月1100元，最长可享受2年

**二、一次性创业补贴**

- **适用对象**：高校在校生及毕业2年内的高校毕业生
- **基本条件**：
  - 首次创业
  - 依法连续缴纳社会保险满6个月及以上
  - 申请时市场主体登记注册在3年以内
- **补贴标准**：2000元；符合吸纳就业条件的，补贴为1万元

---

**官方依据**：
- 创业社会保险补贴办事指南：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
- 一次性创业补贴办事指南：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml

---

由于目前暂未获取到您的毕业时间、社保缴纳情况及企业注册时间等信息，暂时无法确认您具体符合哪项政策。如您需要进一步判断是否符合条件，可以补充以下信息：
- 毕业时间（或是否在校）
- 社保连续缴纳时长
- 企业登记注册时间

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
就业创业 - 苏州市人民政府
发布时间：2026-09-02
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/fed0633326414bb788e341cb4ca2fe9d.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
在线等！第十八届创业周有啥精彩分项，邀您来策划！_图片新闻_苏州市人力资源和社会保障局
发布时间：2026-03-18
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/tpxwr/202603/011c8ae9c3ff4a028d7214d4048b4853.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
2026年度苏州重大创新团队项目申报启动 - 苏州市人民政府
发布时间：2026-03-10
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202603/87f80337a0bb467aa3f61069284144bf.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
关于组织申报2026年度第一批苏州创新创业领军人才计划项目的通知 - 苏州市人民政府
发布时间：2025-12-02
官方来源：https://www.suzhou.gov.cn/szsrmzf/zwgg/202512/c357e36dc6b446df947c384292513a5c.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/wdk.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：18/18
- 严重级别：无
- 问题：无

### C13 / Turn 1：POLICY_FACT

- 输入：创业社会保险补贴需要什么条件
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：已找到以下政策资料：
《创业社会保险补贴》
申请条件：毕业5年内高校毕业生。；依法连续缴纳社保1年及以上。；申请时登记注册在3年以内。
申请材料：《苏州市创业社会保险补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
《一次性创业补贴》
申请条件：高校毕业生毕业2年内。；依法连续缴纳社保6个月及以上。；申请时登记注册在3年以内。
申请材料：《苏州市一次性创业补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
发布时间：2026-06-17
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
常熟市2026年5月份创业服务各类补贴公示 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/shbx/202605/c677a7ad26124b11a9adb0e739209982.shtml
发布时间：2026-05-15
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C14 / Turn 1：POLICY_FACT

- 输入：就业见习适合哪些毕业生
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：已找到以下政策资料：
《就业见习》
申请条件：2024官方问答所列的毕业后两年内未就业人员条件，尚未由2025/2026苏州个人申领口径完整确认。；2024官方问答所列的未就业条件，尚未由2025/2026苏州个人申领口径完整确认。
申请材料：以最新见习单位或人社经办渠道要求为准
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
《求职创业补贴（2026届毕业生申领通知）》
申请条件：本通知适用于毕业学年为2026年的毕业生。；有就业创业意愿。；属于通知列举困难身份之一。
申请材料：低保证明或家庭认定材料；残疾证；国家助学贷款证明；其他困难身份认定材料
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxdt/202508/8bfa1e3fd5b84b23a16f5daa3df5e7c3.shtml
时效提示：该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
致2026届高校毕业生的一封信 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
发布时间：2026-08-03
该通知尚未完成结构化核验，不能据此自动判断个人资格。
苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
发布时间：2026-07-31
该通知尚未完成结构化核验，不能据此自动判断个人资格。
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
发布时间：2026-06-24
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
中小微企业吸纳重点群体就业 社保补贴申领延至下月底 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/szyw/202605/d95c5e2bed314efe8be23e3c998001b9.shtml
发布时间：2026-05-03
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C15 / Turn 1：POLICY_FACT

- 输入：一次性创业补贴有多少钱
- Goal：POLICY_DISCOVERY（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-one-time-2023, suzhou-startup-social-2021
- 追问：无
- 回复：根据苏州官方办事指南（2026-06-17 发布），**一次性创业补贴**的金额如下：

- **基本标准：2000元**
- **符合吸纳就业条件的：1万元**

**申领基本条件**（供参考）：
1. 高校毕业生毕业2年内；
2. 依法连续缴纳社保6个月及以上；
3. 申请时登记注册在3年以内。

官方来源：苏州市人力资源和社会保障局《一次性创业补贴申领办事指南》
https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml

---

💡 **相关支持方向**：如果你已创业并持续经营，还可关注 **创业社会保险补贴**（毕业5年内高校毕业生创办主体、连续缴纳社保满1年、登记在3年内可申请，每月1100元，最长2年）。这两个补贴可以搭配申请，帮你减轻创业初期的负担。

需要我帮你判断是否符合其中某项补贴的申领条件吗？

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
一次性创业补贴申领办事指南 - 高校毕业生就业创业
发布时间：2026-06-17
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml
该证据与本地政策存在可靠关联；网页内容未覆盖本地资格规则，更新内容仍需人工核验。
求职创业补贴申报5月31日截止 - 苏州市人民政府
发布时间：2026-05-29
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：16/18
- 严重级别：P1
- 问题：目标误判：期望 POLICY_FACT，实际 POLICY_DISCOVERY

### C16 / Turn 1：POLICY_FACT

- 输入：灵活就业社保补贴是什么
- Goal：POLICY_DISCOVERY（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-flexible-social-2021, suzhou-employment-internship-2024, suzhou-startup-social-2021
- 追问：无
- 回复：# 灵活就业社会保险补贴

这是一项面向**灵活就业的高校毕业生**的社会保险缴费补贴政策。简单来说，就是对本市户籍、离校2年内未就业的高校毕业生，在灵活就业并参保缴费后，政府按其**缴费额的一定比例**给予补贴，帮助减轻个人社保缴费负担。

## 核心内容（以2026-07-31苏州市青年就业创业政策清单为依据）

**补贴标准**：按个人实际缴费额的 **50%** 给予补贴，期限最长 **2年**。

**申请条件**（须同时满足）：
1. 具有**本市户籍**；
2. **离校2年内**；
3. **未就业**的高校毕业生；
4. **灵活就业**参保并缴费。

**官方来源**：苏州市人民政府高校毕业生就业创业政策清单
https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml

---

## 相关支持方向（供你参考）

如果你对这类就业补贴感兴趣，可能还适合了解以下方向：

- **创业社会保险补贴**：毕业5年内高校毕业生创办主体，连续缴纳社保满1年、登记在3年内可申请，每月1100元、最长2年。
- **就业见习**：面向毕业后两年内未就业人员的见习支持（该方向个人资格条件目前仅由2024官方问答佐证，需人工核验，暂不能单独作为资格判断依据）。

---

需要我帮你**判断是否符合灵活就业社保补贴的申请条件**，或者进一步了解**就业见习**吗？如果你能告知户籍、毕业时间和就业状态，我可以更准确地帮你核对。

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
扩大社保补贴范围，政策延长了！ - 苏州市人民政府
发布时间：2026-09-03
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202609/c819dc688c404ecb990f69b3a78123e2.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
就业创业 - 苏州市人民政府
发布时间：2026-09-02
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/ad1909e2cf2d49c0bcba0f40f70e1801.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
发布时间：2026-06-17
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
该证据与本地政策存在可靠关联；网页内容未覆盖本地资格规则，更新内容仍需人工核验。
求职创业补贴申报5月31日截止 - 苏州市人民政府
发布时间：2026-05-29
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：16/18
- 严重级别：P1
- 问题：目标误判：期望 POLICY_FACT，实际 POLICY_DISCOVERY

### C17 / Turn 1：ELIGIBILITY_CHECK

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：要判断你是否符合当前政策，还需要确认：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 得分：18/18
- 严重级别：无
- 问题：无

### C18 / Turn 1：ELIGIBILITY_CHECK

- 输入：我2026年6月毕业，现在未就业，我符合就业见习吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-employment-internship-2024, suzhou-flexible-social-2021
- 追问：请问您是否具有本市户籍？；请提供您的毕业日期，以便准确核验毕业年限。
- 回复：要判断你是否符合当前政策，还需要确认：请问您是否具有本市户籍？；请提供您的毕业日期，以便准确核验毕业年限。
- 得分：18/18
- 严重级别：无
- 问题：无

### C19 / Turn 1：ELIGIBILITY_CHECK

- 输入：我是太仓户籍，可以申请吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-one-time-2023, suzhou-startup-social-2021
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：要判断你是否符合当前政策，还需要确认：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 得分：18/18
- 严重级别：无
- 问题：无

### C20 / Turn 1：ELIGIBILITY_CHECK

- 输入：我自己交社保，能申请灵活就业补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-flexible-social-2021, suzhou-startup-social-2021, suzhou-job-seeking-subsidy-2026
- 追问：请问您是否具有本市户籍？；请提供您的毕业日期，以便准确核验毕业年限。
- 回复：要判断你是否符合当前政策，还需要确认：请问您是否具有本市户籍？；请提供您的毕业日期，以便准确核验毕业年限。
- 得分：18/18
- 严重级别：无
- 问题：无

### C21 / Turn 1：APPLICATION_GUIDE

- 输入：创业社会保险补贴怎么办理
- Goal：APPLICATION_GUIDE（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → policy_search → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：《创业社会保险补贴》可按以下流程了解和办理：
办理流程：现场办理
参考材料：《苏州市创业社会保险补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
具体受理要求请以官方办事指南为准。
- 得分：18/18
- 严重级别：无
- 问题：无

### C22 / Turn 1：APPLICATION_GUIDE

- 输入：就业见习怎么申请
- Goal：APPLICATION_GUIDE（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → policy_search → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：《就业见习》可按以下流程了解和办理：
办理流程：通过江苏人社网办大厅、江苏智慧人社、江苏省智慧就业云平台或“苏周到”查看岗位并申请
参考材料：以最新见习单位或人社经办渠道要求为准
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
具体受理要求请以官方办事指南为准。
- 得分：18/18
- 严重级别：无
- 问题：无

### C23 / Turn 1：APPLICATION_GUIDE

- 输入：创业社会保险补贴需要准备什么材料
- Goal：POLICY_FACT（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：已找到以下政策资料：
《创业社会保险补贴》
申请条件：毕业5年内高校毕业生。；依法连续缴纳社保1年及以上。；申请时登记注册在3年以内。
申请材料：《苏州市创业社会保险补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
《一次性创业补贴》
申请条件：高校毕业生毕业2年内。；依法连续缴纳社保6个月及以上。；申请时登记注册在3年以内。
申请材料：《苏州市一次性创业补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
发布时间：2026-06-17
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
常熟市2026年5月份创业服务各类补贴公示 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/shbx/202605/c677a7ad26124b11a9adb0e739209982.shtml
发布时间：2026-05-15
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：16/18
- 严重级别：P1
- 问题：目标误判：期望 APPLICATION_GUIDE，实际 POLICY_FACT

### C24 / Turn 1：APPLICATION_GUIDE

- 输入：创业社会保险补贴去哪里申请
- Goal：POLICY_DISCOVERY（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：根据你目前提供的信息，可先了解：创业社会保险补贴、一次性创业补贴。

相关官方公开信息：
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
发布时间：2026-06-17
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
常熟市2026年5月份创业服务各类补贴公示 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/shbx/202605/c677a7ad26124b11a9adb0e739209982.shtml
发布时间：2026-05-15
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：14/18
- 严重级别：P0, P1
- 问题：目标误判：期望 APPLICATION_GUIDE，实际 POLICY_DISCOVERY；无画像时出现个性化断言

### C25 / Turn 1：多轮：资格续接

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：要判断你是否符合当前政策，还需要确认：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 得分：18/18
- 严重级别：无
- 问题：无

### C25 / Turn 2：多轮：资格续接

- 输入：有昆山市户籍
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：根据已核验的创业社会保险补贴政策，其申请条件为：

1. 毕业5年内高校毕业生；
2. 依法连续缴纳社保满1年及以上；
3. 申请时登记注册在3年以内。

户籍（昆山市）并不是该政策的申请条件，因此仅凭户籍信息无法判断您是否符合。要完成核验，还需要您提供：
- 您的毕业日期（用于核验是否在毕业5年内）；
- 您连续缴纳社保的月数（是否已满1年）。

您可以补充这两项信息，我再为您继续核验。
- 得分：18/18
- 严重级别：无
- 问题：无

### C26 / Turn 1：多轮：目标切换

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：根据当前已核验的官方办事指南，**创业社会保险补贴**的申请条件包括以下三项：

1. **毕业5年内**的高校毕业生；
2. 依法**连续缴纳社保满1年及以上**；
3. 申请时**登记注册在3年以内**。

目前我还没有您个人的相关信息，暂时**无法确认您是否符合**。要为您做准确判断，还需要您补充以下信息：

- 您的**毕业日期**（用于核验是否在毕业5年内）；
- 您**连续缴纳社保的月数**（是否已满12个月）；
- 您创办主体（公司/个体户）的**登记注册时间**（是否在3年以内）。

您提供后我会逐一为您核验。另外提醒一下，若您属于**毕业2年内**首次创业，也可能符合**一次性创业补贴**（连续缴社保满6个月、注册3年内，补贴2000元），如需了解可以一并告诉我。

请问以上三项信息您能提供吗？
- 得分：18/18
- 严重级别：无
- 问题：无

### C26 / Turn 2：多轮：目标切换

- 输入：先不管补贴了，我只想找工作
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：如果你的目标是尽快找工作，当前可优先关注就业见习、求职创业补贴（2026届毕业生申领通知）。

相关官方公开信息：
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
追加1亿元，苏州将接续汽车购新补贴 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202606/21c2fb79165f4b5eaa6fe5732acd194a.shtml
发布时间：2026-06-22
该通知尚未完成结构化核验，不能据此自动判断个人资格。
苏州市2026年汽车购新补贴开启申领 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202604/d80f90784ddc45afb4e8c0667c97cab3.shtml
发布时间：2026-04-04
该通知尚未完成结构化核验，不能据此自动判断个人资格。
苏州人才政策申报月历（2026版） - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202603/f6ed78aaaafc4bc6897e60ae79f81751.shtml
发布时间：2026-03-03
该通知尚未完成结构化核验，不能据此自动判断个人资格。
江苏发布2026以旧换新补贴政策 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202601/e6868dc3c5144de394348a9e15786435.shtml
发布时间：2026-01-23
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C27 / Turn 1：多轮：画像纠正

- 输入：我在苏州，本科，今年毕业，目前待就业
- Goal：PROFILE_UPDATE（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：暂未找到与当前信息高度相关的政策，可以补充地区、毕业时间或就业创业情况后继续查询。
- 得分：13/18
- 严重级别：P1
- 问题：目标误判：期望 POLICY_DISCOVERY，实际 PROFILE_UPDATE；检索边界不符合预期

### C27 / Turn 2：多轮：画像纠正

- 输入：之前说错了，其实我是硕士
- Goal：PROFILE_UPDATE（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：好的，已把你的学历信息更新为**硕士**。目前你的情况是：

- 地区：苏州市
- 学历：硕士
- 毕业年份：2026年
- 就业状态：待就业

需要我帮你查询苏州针对**硕士毕业生**的就业创业相关政策吗？比如社保补贴、租房/生活补贴、创业扶持等，告诉我你的具体需求即可。
- 得分：13/18
- 严重级别：P1
- 问题：目标误判：期望 POLICY_DISCOVERY，实际 PROFILE_UPDATE；检索边界不符合预期

### C28 / Turn 1：多轮：短追问

- 输入：创业社会保险补贴需要什么条件
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：已找到以下政策资料：
《创业社会保险补贴》
申请条件：毕业5年内高校毕业生。；依法连续缴纳社保1年及以上。；申请时登记注册在3年以内。
申请材料：《苏州市创业社会保险补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
《一次性创业补贴》
申请条件：高校毕业生毕业2年内。；依法连续缴纳社保6个月及以上。；申请时登记注册在3年以内。
申请材料：《苏州市一次性创业补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
发布时间：2026-06-17
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
常熟市2026年5月份创业服务各类补贴公示 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/shbx/202605/c677a7ad26124b11a9adb0e739209982.shtml
发布时间：2026-05-15
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C28 / Turn 2：多轮：短追问

- 输入：那我可以吗
- Goal：POLICY_FACT（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：要判断您是否符合“创业社会保险补贴”的申请条件，我需要了解您以下三项信息：

1. **毕业时间**——政策要求毕业5年内的高校毕业生
2. **社保缴纳情况**——是否依法连续缴纳社保1年及以上
3. **注册时间**——您创办的经营主体登记注册是否在3年以内

目前这些信息我还没有，暂时无法确认您是否符合。您可以告诉我这几点，我再帮您核对。

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
关于组织开展2026年度苏州市“独角兽”培育企业申报工作的通知 - 苏州市人民政府
发布时间：2026-09-17
官方来源：https://www.suzhou.gov.cn/szsrmzf/bmwj/202609/2eea6997174842779f78bbe710d30f0b.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
2026年苏州高技能人才计划启动申报 - 苏州市人民政府
发布时间：2026-04-29
官方来源：https://www.suzhou.gov.cn/szsrmzf/zwgg/202604/56232835320043e9a173aaa397f1a742.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
苏州人才政策申报月历（2026版） - 苏州市人民政府
发布时间：2026-03-03
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202603/f6ed78aaaafc4bc6897e60ae79f81751.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
就业创业 - 苏州市人民政府
发布时间：2026-02-06
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202602/84c92e2dc283416aa5f66abebdf95836.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：16/18
- 严重级别：P1
- 问题：目标误判：期望 ELIGIBILITY_CHECK，实际 POLICY_FACT

### C29 / Turn 1：多轮：下一步

- 输入：我是2026届毕业生，现在有什么就业支持
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：根据你目前提供的信息，可先了解：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴。

相关官方公开信息：
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
2026年苏州高新区教育系统公开招聘优秀毕业生公告_通知公告_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/gsgg/202603/53a976d2a3664e6da73e7902431f9ac6.shtml
发布时间：2026-03-09
该通知尚未完成结构化核验，不能据此自动判断个人资格。
苏州工业园区教育系统公开招聘2026年高层次优秀毕业生公告_通知公告_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/gsgg/202512/55fcbfde52dd4466af02c08e0f931beb.shtml
发布时间：2025-12-26
该通知尚未完成结构化核验，不能据此自动判断个人资格。
苏州市教育局直属学校赴高校公开招聘2026年高层次优秀毕业生公告_通知公告_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/gsgg/202512/58688103d83249f783f5ddee3770c46a.shtml
发布时间：2025-12-10
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C29 / Turn 2：多轮：下一步

- 输入：那下一步呢
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-flexible-social-2021, suzhou-employment-internship-2024
- 追问：无
- 回复：好的，围绕你“2026届毕业生”的身份，目前可核验的支持方向主要有两个：**灵活就业社会保险补贴**和**就业见习**。下面分别说明，供你参考下一步。

---

**方向一：灵活就业社会保险补贴**

- **政策依据**：以2026-07-31苏州市青年就业创业政策清单为准。
- **主要内容**：本市户籍离校2年内未就业高校毕业生，灵活就业参保并缴费的，按其缴费额50%给予补贴，期限最长2年。
- **申请条件**：
  1. 具有本市户籍；
  2. 离校2年内；
  3. 未就业高校毕业生；
  4. 灵活就业参保并缴费。

**说明**：你目前仅确认了毕业年份（2026），是否满足本市户籍、离校后未就业等条件暂无法判断。若你考虑灵活就业，可对照以上条件准备。

---

**方向二：就业见习**

- **政策依据**：2026-07-31政策清单确认就业见习政策仍在列，但该来源未完整列明个人资格条件。
- **补充说明**：2024官方问答曾列有“毕业后两年内未就业人员”等条件，但尚未由2025/2026苏州个人申领口径完整确认，因此不能单独作为当前资格判断依据。

**说明**：如果你希望先通过见习积累经验，可进一步向当地人社部门咨询最新申领口径。

---

**下一步建议**：你可以告诉我更倾向哪个方向，或者是否需要我帮你梳理某一项的具体办理流程。

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
关于组织开展2026年度苏州市“独角兽”培育企业申报工作的通知 - 苏州市人民政府
发布时间：2026-09-17
官方来源：https://www.suzhou.gov.cn/szsrmzf/bmwj/202609/2eea6997174842779f78bbe710d30f0b.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
2026年苏州高技能人才计划启动申报 - 苏州市人民政府
发布时间：2026-04-29
官方来源：https://www.suzhou.gov.cn/szsrmzf/zwgg/202604/56232835320043e9a173aaa397f1a742.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
苏州人才政策申报月历（2026版） - 苏州市人民政府
发布时间：2026-03-03
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202603/f6ed78aaaafc4bc6897e60ae79f81751.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
就业创业 - 苏州市人民政府
发布时间：2026-02-06
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202602/84c92e2dc283416aa5f66abebdf95836.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：18/18
- 严重级别：无
- 问题：无

### C30 / Turn 1：多轮：历史后致谢

- 输入：2026届求职创业补贴什么时候申报
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-startup-social-2021
- 追问：无
- 回复：已找到以下政策资料：
《求职创业补贴（2026届毕业生申领通知）》
申请条件：本通知适用于毕业学年为2026年的毕业生。；有就业创业意愿。；属于通知列举困难身份之一。
申请材料：低保证明或家庭认定材料；残疾证；国家助学贷款证明；其他困难身份认定材料
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxdt/202508/8bfa1e3fd5b84b23a16f5daa3df5e7c3.shtml
时效提示：该记录为历史申报通知，申报窗口已结束。请关注苏州市人社部门后续发布的最新年度申报安排。
《创业社会保险补贴》
申请条件：毕业5年内高校毕业生。；依法连续缴纳社保1年及以上。；申请时登记注册在3年以内。
申请材料：《苏州市创业社会保险补贴申请表》；营业执照或其他法定注册登记证书；毕业证书；实地经营照片
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
9月1日起，一次性求职补贴启动申请！ - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/4c8011508d454b5daca189413781e1ab.shtml
发布时间：2026-08-28
该通知尚未完成结构化核验，不能据此自动判断个人资格。
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职补贴！线上申报！_人社要闻_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxdt/202508/8bfa1e3fd5b84b23a16f5daa3df5e7c3.shtml
发布时间：2025-08-27
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/wdk.shtml
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C30 / Turn 2：多轮：历史后致谢

- 输入：谢谢
- Goal：CONVERSATIONAL（期望 CONVERSATIONAL）
- 节点：resolve_goal → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：不客气。需要了解政策、办理流程或资格判断时，随时告诉我。
- 得分：18/18
- 严重级别：无
- 问题：无

## 优化优先级

- P0：先处理任何金额/资格无证据断言或跨会话画像泄露。
- P1：处理目标误判、检索边界和历史政策时效提示。
- P2：优化建议动作的针对性、回复简洁度和响应时延。
