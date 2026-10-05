# 青程 Agent 真实场景 Benchmark 报告

## 总体得分

- 总分：646/648（99.7%）
- 评测轮数：36
- Goal Accuracy：100.0%
- Retrieval Precision：100.0%
- 官方来源占比：100.0%
- 平均响应时间：18404 ms
- P0：0；P1：0

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
- 回复：如果你的目标是尽快找工作，可优先关注高校毕业生招聘、官方就业服务和就业见习机会。
当前可关注的官方就业服务信息：
- 致2026届高校毕业生的一封信 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
- 苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
- 就业创业 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
下一步可先查看就业见习要求，或查询当地近期高校毕业生招聘活动。

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
- 回复：如果你的目标是尽快找工作，可优先关注高校毕业生招聘、官方就业服务和就业见习机会。
当前可关注的官方就业服务信息：
- 致2026届高校毕业生的一封信 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
- 苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
- 就业创业 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
下一步可先查看就业见习要求，或查询当地近期高校毕业生招聘活动。

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
- 得分：18/18
- 严重级别：无
- 问题：无

### C07 / Turn 1：JOB_SEARCH

- 输入：我不想创业，只想就业
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：如果你的目标是尽快找工作，可优先关注高校毕业生招聘、官方就业服务和就业见习机会。
当前可关注的官方就业服务信息：
- 致2026届高校毕业生的一封信 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
- 苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
- 就业创业 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
下一步可先查看就业见习要求，或查询当地近期高校毕业生招聘活动。

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
- 得分：18/18
- 严重级别：无
- 问题：无

### C08 / Turn 1：JOB_SEARCH

- 输入：苏州最近有什么适合毕业生的就业服务
- Goal：JOB_SEARCH（期望 JOB_SEARCH）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：如果你的目标是尽快找工作，可优先关注高校毕业生招聘、官方就业服务和就业见习机会。
当前可关注的官方就业服务信息：
- 致2026届高校毕业生的一封信 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
- 苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
- 就业创业 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
下一步可先查看就业见习要求，或查询当地近期高校毕业生招聘活动。

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
- 得分：18/18
- 严重级别：无
- 问题：无

### C09 / Turn 1：POLICY_DISCOVERY

- 输入：苏州毕业生现在有什么就业支持
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：NO_RESULTS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：目前可优先了解：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴、一次性创业补贴。

已完成官方信息查询，当前未发现新的相关公开通知。
- 得分：18/18
- 严重级别：无
- 问题：无

### C10 / Turn 1：POLICY_DISCOVERY

- 输入：我今年毕业，有什么政策可以看看
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：根据你目前已确认的信息：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴。
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
- 回复：目前可优先了解：创业社会保险补贴、一次性创业补贴。

相关官方公开信息：
就业创业 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202609/fed0633326414bb788e341cb4ca2fe9d.shtml
发布时间：2026-09-02
该通知尚未完成结构化核验，不能据此自动判断个人资格。
在线等！第十八届创业周有啥精彩分项，邀您来策划！_图片新闻_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/tpxwr/202603/011c8ae9c3ff4a028d7214d4048b4853.shtml
发布时间：2026-03-18
该通知尚未完成结构化核验，不能据此自动判断个人资格。
2026年度苏州重大创新团队项目申报启动 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202603/87f80337a0bb467aa3f61069284144bf.shtml
发布时间：2026-03-10
该通知尚未完成结构化核验，不能据此自动判断个人资格。
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
以上为政策事实说明，不代表对您个人资格的判断。

相关官方公开信息：
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
发布时间：2026-06-17
致2026届高校毕业生的一封信 - 高校毕业生就业创业
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发布时间：2026-08-13
该通知尚未完成结构化核验，不能据此自动判断个人资格。
求职创业补贴申报5月31日截止 - 苏州市人民政府
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发布时间：2026-05-29
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C14 / Turn 1：POLICY_FACT

- 输入：就业见习适合哪些毕业生
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：NO_RESULTS
- 政策：suzhou-employment-internship-2024, suzhou-job-seeking-subsidy-2026
- 追问：无
- 回复：已找到以下政策资料：
《就业见习》
申请条件：2024官方问答所列的毕业后两年内未就业人员条件，尚未由2025/2026苏州个人申领口径完整确认。；2024官方问答所列的未就业条件，尚未由2025/2026苏州个人申领口径完整确认。
申请材料：以最新见习单位或人社经办渠道要求为准
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
以上为政策事实说明，不代表对您个人资格的判断。

已完成官方信息查询，当前未发现新的相关公开通知。
- 得分：18/18
- 严重级别：无
- 问题：无

### C15 / Turn 1：POLICY_FACT

- 输入：一次性创业补贴有多少钱
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：NO_RESULTS
- 政策：suzhou-startup-one-time-2023, suzhou-startup-social-2021
- 追问：无
- 回复：根据已核验的政策信息，苏州市一次性创业补贴的金额如下：

- **基础补贴：2000元**
- **符合吸纳就业条件的：1万元**

需要说明的是，申领该补贴需满足以下条件：
1. 高校毕业生毕业2年内；
2. 依法连续缴纳社保6个月及以上；
3. 申请时登记注册在3年以内。

官方依据来源：苏州市政府高校毕业生就业创业栏目办事指南（https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202302/96da57a1d6154b0f939db183e13ee4af.shtml）

如果你需要了解**办理流程**，或想**判断自己是否符合**申领条件，我可以继续帮你查询。

已完成实时查询，当前未从已配置的官方来源中发现新的相关公开通知。
- 得分：18/18
- 严重级别：无
- 问题：无

### C16 / Turn 1：POLICY_FACT

- 输入：灵活就业社保补贴是什么
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：NO_RESULTS
- 政策：suzhou-flexible-social-2021, suzhou-employment-internship-2024, suzhou-startup-social-2021
- 追问：无
- 回复：灵活就业社会保险补贴，是苏州市面向**离校2年内未就业的本市户籍高校毕业生**的一项就业扶持政策。

简单来说，就是你在灵活就业期间自行参保并缴纳社会保险费的，政府会按你**缴费额的50%**给予补贴，补贴期限**最长不超过2年**。

申请该补贴需要同时满足以下条件：
- 具有**本市户籍**；
- 属于**离校2年内**的高校毕业生；
- **未就业**（处于灵活就业状态）；
- 已**灵活就业参保并缴费**。

官方政策依据：苏州市青年就业创业政策清单（2026-07-31版）
来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml

需要的话，我可以帮你看看**具体办理流程**，或者帮你**判断自己是否符合条件**，你想了解哪一项？

已完成实时查询，当前未从已配置的官方来源中发现新的相关公开通知。
- 得分：18/18
- 严重级别：无
- 问题：无

### C17 / Turn 1：ELIGIBILITY_CHECK

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
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
- 政策：suzhou-employment-internship-2024
- 追问：无
- 回复：根据你目前的情况，我为你说明一下就业见习的资格核验结果（以下均来自已核验的政策信息，不做主观推断）：

**目前能确认的部分**
- 你当前处于**未就业**状态，这一项条件可以确认满足。

**暂无法确认的部分**
1. **政策时效性**：就业见习政策目前的有效性尚未由最新官方口径完整确认，因此暂时不能作为当前申请的依据。
2. **“毕业后两年内未就业”条件**：这一条件来自2024年的官方问答，但尚未由2025/2026年苏州的个人申领口径完整确认，因此目前无法确认你是否满足。

**结论**
由于上述关键条件（尤其“毕业后两年内未就业”的现行口径）尚未得到当前官方确认，目前**不能直接确认你符合就业见习资格**，需要进一步的人工复核或官方核验后才能确定。

**建议**
- 你可以留意苏州市人社局/政府官网的最新申报通知，确认政策当前是否有效及个人申领条件。
- 如需，我可以帮你检索官方最新的政策与申报动态，或在你完善画像后再次核验。

需要我帮你查询官方最新申报状态或整理相关材料要求吗？
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
- 政策：suzhou-startup-social-2021
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
- 政策：suzhou-employment-internship-2024
- 追问：无
- 回复：就业见习的申请渠道已核验，具体如下：

**申请渠道**
您可通过以下任一官方平台查看岗位并提交申请：
- 江苏人社网办大厅
- 江苏智慧人社
- 江苏省智慧就业云平台
- “苏周到”App

**关于资格条件**
需要说明的是，2026年7月31日的政策清单确认就业见习政策仍在列，但该来源未完整列明个人资格条件。目前可参考的是2024年官方问答所列条件（如毕业后两年内未就业等），但这些条件尚未由2025/2026年苏州个人申领口径完整确认，因此暂无法据此判断您个人是否符合，最终以人社经办部门审核为准。

**参考材料**
具体材料要求以最新见习单位或人社经办渠道要求为准，建议在申请时直接向受理部门确认。

**官方来源**
苏州市政府就业创业政策清单：
https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml

如需进一步确认您个人是否符合条件，可告诉我您的毕业时间等基本情况，我帮您梳理需要向人社部门核实的关键点。
- 得分：18/18
- 严重级别：无
- 问题：无

### C23 / Turn 1：APPLICATION_GUIDE

- 输入：创业社会保险补贴需要准备什么材料
- Goal：APPLICATION_GUIDE（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → policy_search → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
- 追问：无
- 回复：根据苏州市创业社会保险补贴的办事指南，申请时需要准备以下材料：

**申请材料**
1. **《苏州市创业社会保险补贴申请表》**
2. **营业执照**或其他法定注册登记证书
3. **毕业证书**
4. **实地经营照片**

**办理方式**
- 以上材料通过**现场办理**提交。

**申请条件（供参考）**
- 毕业5年内高校毕业生；
- 依法连续缴纳社保1年及以上；
- 申请时登记注册在3年以内。

**官方来源**
- 苏州市人民政府网站：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml

需要说明的是，以上材料清单和条件以官方办事指南为依据，最终请以政府部门最新规定和审核为准。

如果你愿意，我可以帮你进一步判断是否符合申请条件，或核对各项材料的准备情况。需要吗？
- 得分：18/18
- 严重级别：无
- 问题：无

### C24 / Turn 1：APPLICATION_GUIDE

- 输入：创业社会保险补贴去哪里申请
- Goal：APPLICATION_GUIDE（期望 APPLICATION_GUIDE）
- 节点：resolve_goal → merge_profile → policy_search → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
- 追问：无
- 回复：根据苏州市2026年6月17日的办事指南，创业社会保险补贴需要**现场办理**。具体说明如下：

**申请条件**
- 毕业5年内高校毕业生；
- 依法连续缴纳社保1年及以上；
- 申请时登记注册在3年以内。

**参考材料**
1. 《苏州市创业社会保险补贴申请表》；
2. 营业执照或其他法定注册登记证书；
3. 毕业证书；
4. 实地经营照片。

**办理方式**
- 流程为现场办理，办事指南中未列明具体受理窗口或线上入口。

**官方来源**
苏州市人力资源和社会保障局办事指南：
https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml

由于当前信息未明确具体受理地点，建议您携带上述材料，联系注册地所在区的人社部门或创业服务经办机构确认现场受理窗口。政策依据以政府部门最新规定和审核为准。
- 得分：18/18
- 严重级别：无
- 问题：无

### C25 / Turn 1：多轮：资格续接

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
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
- 政策：suzhou-startup-social-2021
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：明白，您有昆山市户籍。不过需要说明的是，**创业社会保险补贴**的申请条件并不包含户籍要求，它的核心条件是以下三项：

1. 毕业5年内的高校毕业生；
2. 依法连续缴纳社保满1年及以上；
3. 申请时登记注册在3年以内。

所以要判断您是否符合，我还需要您确认两个关键信息：

- 您的**毕业日期**（用于核验是否在毕业5年内）；
- 您**连续缴纳社会保险的月数**（用于核验是否满1年）。

您能提供这两项信息吗？
- 得分：18/18
- 严重级别：无
- 问题：无

### C26 / Turn 1：多轮：目标切换

- 输入：我符合创业社会保险补贴吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：要判断你是否符合当前政策，还需要确认：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
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
- 回复：如果你的目标是尽快找工作，可优先关注高校毕业生招聘、官方就业服务和就业见习机会。
当前可关注的官方就业服务信息：
- 致2026届高校毕业生的一封信 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/mszx/202608/c7a0959c47144740999b5a82f850a6ab.shtml
- 苏州市高校毕业生等青年就业创业政策清单 - 高校毕业生就业创业：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202508/dba4deacb2a7480ea4ae806417831faa.shtml
- 就业创业 - 苏州市人民政府：https://www.suzhou.gov.cn/szsrmzf/rdwd3/202606/3dda2f82b1644e5cb20f4154f8737612.shtml
下一步可先查看就业见习要求，或查询当地近期高校毕业生招聘活动。

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
- 得分：18/18
- 严重级别：无
- 问题：无

### C27 / Turn 1：多轮：画像纠正

- 输入：我在苏州，本科，今年毕业，目前待就业
- Goal：PROFILE_UPDATE（期望 PROFILE_UPDATE）
- 节点：resolve_goal → merge_profile → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：暂未找到与当前信息高度相关的政策，可以补充地区、毕业时间或就业创业情况后继续查询。
- 得分：17/18
- 严重级别：无
- 问题：无

### C27 / Turn 2：多轮：画像纠正

- 输入：之前说错了，其实我是硕士
- Goal：PROFILE_UPDATE（期望 PROFILE_UPDATE）
- 节点：resolve_goal → merge_profile → presentation
- 搜索：False；实时状态：NOT_TRIGGERED
- 政策：无
- 追问：无
- 回复：好的，已帮你把学历从“本科”更正为 **硕士**。

目前你的个人情况是：
- 地区：苏州市
- 学历：硕士
- 毕业年份：2026年
- 就业状态：待就业

需要我根据这个情况帮你查一下苏州针对硕士毕业生有哪些可申报的就业创业政策吗？
- 得分：17/18
- 严重级别：无
- 问题：无

### C28 / Turn 1：多轮：短追问

- 输入：创业社会保险补贴需要什么条件
- Goal：POLICY_FACT（期望 POLICY_FACT）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-startup-social-2021, suzhou-startup-one-time-2023
- 追问：无
- 回复：根据苏州官方办事指南（以2026年6月17日发布的《创业社会保险补贴申领办事指南》为当前依据），申请创业社会保险补贴需同时满足以下条件：

1. **人员身份**：毕业5年内的高校毕业生；
2. **社保缴纳**：依法连续缴纳社会保险费1年及以上；
3. **注册时间**：申请补贴时，登记注册时间须在3年以内。

**补贴标准**：每人每月1100元，补贴期限最长不超过2年。

**办理说明**：符合条件的申请人需在苏州领取营业执照或办理其他法定注册登记手续，并取得加载统一社会信用代码的登记证书后，方可申请。

官方来源：苏州市人力资源和社会保障局《创业社会保险补贴申领办事指南》
https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml

如需进一步了解**办理流程**，或想**判断自己是否符合条件**，可以告诉我，我来帮你进一步核实。

官方检索证据如下；资格判断仍以本地已结构化政策规则为依据。
创业社会保险补贴申领办事指南 - 高校毕业生就业创业
发布时间：2026-06-17
官方来源：https://www.suzhou.gov.cn/gxbysjycy/byszcqd/202309/754cbda52f984e9198bd7e9c2d573d58.shtml
该证据与本地政策存在可靠关联；网页内容未覆盖本地资格规则，更新内容仍需人工核验。
致2026届高校毕业生的一封信 - 高校毕业生就业创业
发布时间：2026-08-13
官方来源：https://www.suzhou.gov.cn/gxbysjycy/bysgzdt/202608/9f5436b494fe467c84e05cf7c74dd995.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
求职创业补贴申报5月31日截止 - 苏州市人民政府
发布时间：2026-05-29
官方来源：https://www.suzhou.gov.cn/szsrmzf/mszx/202605/beea20c882ba4663ab5256aafb893932.shtml
发现新的官方政策/通知，尚未完成结构化核验，暂不能自动判断您是否符合。
- 得分：18/18
- 严重级别：无
- 问题：无

### C28 / Turn 2：多轮：短追问

- 输入：那我可以吗
- Goal：ELIGIBILITY_CHECK（期望 ELIGIBILITY_CHECK）
- 节点：resolve_goal → merge_profile → policy_search → required_fields → eligibility → material → plan → presentation
- 搜索：True；实时状态：NOT_TRIGGERED
- 政策：suzhou-startup-social-2021
- 追问：请提供您的毕业日期，以便准确核验毕业年限。；请问您连续缴纳社会保险已有几个月？
- 回复：要判断您是否符合创业社会保险补贴的条件，我还需要确认两项关键信息：

1. **您的毕业日期**——用于核验"毕业5年内高校毕业生"这一条件；
2. **您已连续缴纳社会保险的月数**——用于核验"依法连续缴纳社保满1年"这一条件。

另外，补贴还要求**申请时登记注册在3年以内**，如果您能一并提供创办主体的注册时间，我也可以帮您一并核实。

您可以告诉我这些信息，我来帮您做准确的资格判断。
- 得分：18/18
- 严重级别：无
- 问题：无

### C29 / Turn 1：多轮：下一步

- 输入：我是2026届毕业生，现在有什么就业支持
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：SUCCESS
- 政策：suzhou-job-seeking-subsidy-2026, suzhou-flexible-social-2021
- 追问：无
- 回复：根据你目前已确认的信息：求职创业补贴（2026届毕业生申领通知）、灵活就业社会保险补贴。

相关官方公开信息：
人力资源社会保障部财政部关于做好2026年高校毕业生等青年就业工作的通知_政策法规库_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/zxfgk/202605/d60ca2b54e9548f39a8370a1528c835f.shtml
发布时间：2026-05-11
该通知尚未完成结构化核验，不能据此自动判断个人资格。
2026年苏州高新区教育系统公开招聘优秀毕业生公告_通知公告_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/gsgg/202603/53a976d2a3664e6da73e7902431f9ac6.shtml
发布时间：2026-03-09
该通知尚未完成结构化核验，不能据此自动判断个人资格。
2026年苏州市吴中区教育系统公开招聘优秀毕业生公告_通知公告_苏州市人力资源和社会保障局
官方来源：https://hrss.suzhou.gov.cn/jsszhrss/gsgg/202602/898b649759f244b79140da48fc07fc58.shtml
发布时间：2026-02-06
该通知尚未完成结构化核验，不能据此自动判断个人资格。
- 得分：18/18
- 严重级别：无
- 问题：无

### C29 / Turn 2：多轮：下一步

- 输入：那下一步呢
- Goal：POLICY_DISCOVERY（期望 POLICY_DISCOVERY）
- 节点：resolve_goal → merge_profile → official_search → policy_search → presentation
- 搜索：True；实时状态：NO_RESULTS
- 政策：suzhou-flexible-social-2021, suzhou-employment-internship-2024
- 追问：无
- 回复：根据你目前已确认的信息：高校毕业生就业创业支持。

已完成官方信息查询，当前未发现新的相关公开通知。
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
