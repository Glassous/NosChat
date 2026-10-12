/**
 * 模型列表与模拟数据（纯前端演示，无真实推理）
 * 每个模型都有自己的风格标签、能力参数与话术模板，用于模拟不同模型的回复差异。
 * reasoning 为 true 的模型会额外生成一段「深度思考」过程，可在界面上展开/折叠。
 * 注：released 为演示用的发布日期（ISO 格式，用于展示与排序）。
 */

export const MODEL_LIST = [
  {
    id: 'deepseek-v3',
    name: 'DeepSeek-V3',
    provider: '深度求索',
    icon: '🐋',
    badge: '推荐',
    color: '#4d6bfe',
    desc: '通用对话能力强，中文理解自然，响应速度快。',
    tags: ['通用', '中文', '性价比'],
    context: '64K',
    released: '2024-12-27',
    speed: 5,
    intelligence: 4,
    temp: 0.7,
    reasoning: false,
    latency: [600, 1200],
    replies: [
      '从通用角度看，你提到的「{q}」可以从三个层面理解：定义、场景、取舍。先明确目标，再选择工具。',
      '关于「{q}」，我的判断是：优先保证可读性和可维护性，再考虑性能优化。',
      '「{q}」这个问题很适合用「先拆分、再验证」的思路处理，我可以帮你把步骤列出来。'
    ]
  },
  {
    id: 'deepseek-r1',
    name: 'DeepSeek-R1',
    provider: '深度求索',
    icon: '🧠',
    badge: '推理',
    color: '#7c3aed',
    desc: '强化推理模型，擅长数学、逻辑与分步推导，会先输出思考链。',
    tags: ['推理', '数学', '逻辑'],
    context: '128K',
    released: '2025-01-20',
    speed: 2,
    intelligence: 5,
    temp: 0.6,
    reasoning: true,
    latency: [1600, 2600],
    thinkLatency: [1200, 2400],
    replies: [
      '结论先行：处理「{q}」的关键是先把目标唯一化，再逐条排除矛盾分支。\n完整推导过程我折叠在上方的「深度思考」里，可以展开核对每一步。',
      '关于「{q}」，我的答案是「先建模、再求解、最后回代验证」。\n中间的检查与回溯写在思考过程中，展开即可看到。',
      '针对「{q}」，我采用反向验证：假设结论不成立会推出与已知条件冲突的结果，因此原结论成立。\n详细链路易较长，已折叠在上方。'
    ],
    thinkTemplates: [
      '先把问题重述一遍：{q}\n\n第一步 · 界定条件\n- 明确已知量、未知量与约束边界；\n- 判断题型：属于「有唯一解」还是「多解需筛选」；\n- 这里我倾向多解筛选，因为题面缺少限定条件。\n\n第二步 · 建立模型\n- 引入最贴近的公式/结构，把自然语言翻成可计算形式；\n- 检查单位与量纲是否一致，避免代入即错。\n\n第三步 · 求解\n- 先做能做的化简，再代入；\n- 中途得到候选值 3 与 7，都不满足第二条约束，舍去；\n- 剩下候选 2，代回原式。\n\n第四步 · 回代验证\n- 用两组独立条件分别验算，均成立；\n- 顺手估计一下边界情况（n=1）是否退化合理，结果正常。\n\n第五步 · 组织回答\n- 结论放最前，理由分点，避免把推导埋在长段落里。',
      '我在想：{q}\n\n- 这句话里的关键约束是什么？我圈出两个词，它们决定了可用方法的范围。\n- 若按常规路径直接展开，会出现组合爆炸；所以我先做一次「对称性/单调性」观察，把解空间砍掉大半。\n- 剩下的分支逐个试探：第一条在第二步自相矛盾；第二条可行。\n- 我还不放心，于是换一种独立方法复算了一遍，结果一致 → 可以给出答案。\n- 回答时我会把「为什么先砍解空间」讲清楚，这比结果本身更有复用价值。',
      '拆解 {q}：\n\n1. 目标：给出可执行结论，而不是概念复述。\n2. 障碍：题面信息不足，存在两种合理解读。\n3. 消歧：取更保守的解读，并在回答里显式声明假设。\n4. 推演：在该假设下走三步，第二步出现一个反例 → 说明解读要修正。\n5. 修正后重走，三步全部通过。\n6. 输出：结论 + 假设声明 + 反例说明，让用户能自行复核。'
    ]
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    provider: 'OpenAI',
    icon: '🛰️',
    badge: '多模态',
    color: '#10a37f',
    desc: '多模态旗舰模型，图文音视频综合表现均衡。',
    tags: ['多模态', '通用', '英文强'],
    context: '128K',
    released: '2024-05-13',
    speed: 4,
    intelligence: 5,
    temp: 0.8,
    reasoning: false,
    latency: [900, 1800],
    replies: [
      'Good question about “{q}”. 我建议按「结构化拆解 + 示例驱动」的方式回答，这样最容易落地。',
      '关于「{q}」，我会先给出结论，再给论据：结论是——先跑通最小闭环，再逐步增强。',
      '从多模态视角看「{q}」，文本、图表、代码三类信息混合表达时效率最高，我可以按这个格式输出。'
    ]
  },
  {
    id: 'claude-3-7',
    name: 'Claude 3.7 Sonnet',
    provider: 'Anthropic',
    icon: '🎯',
    badge: '长文',
    color: '#d97757',
    desc: '支持 extended thinking，长文档与代码重构表现优秀。',
    tags: ['推理', '编程', '长文档'],
    context: '200K',
    released: '2025-02-24',
    speed: 3,
    intelligence: 5,
    temp: 0.5,
    reasoning: true,
    latency: [1100, 2000],
    thinkLatency: [900, 1800],
    replies: [
      '我会这样处理「{q}」：先写清接口契约，再拆成可独立测试的阶段，最后才谈性能。\n我先把边界条件与风险点摊开，再给顺序。\n（extended thinking 过程已折叠在上方）',
      '关于「{q}」，关键是先建立可读骨架，再用测试锁定行为。\n需要特别注意那几处「看起来像 bug 但已被下游依赖」的特例，建议单列为兼容层。',
      '「{q}」我会分三条路径说明：正常路径、异常路径、回滚路径。分开说能避免边界条件被忽略。'
    ],
    thinkTemplates: [
      'Reframing the request — {q}\n\n1) 意图确认：用户要的是「可落地的改造顺序」，不是概念科普。\n2) 现状扫描：2000 行的函数意味着至少 3 处隐性耦合（状态共享、时间依赖、外部副作用）。\n3) 风险排序：最危险的不是行数，而是「未被记录的特例」。动结构前必须先把特例锁成测试。\n4) 拆分策略：按业务语义而非代码长度切分——校验 / 计价 / 库存 / 支付 / 通知，每段保持纯函数，输入输出显式。\n5) 迁移顺序：先加测试（不改行为）→ 再抽函数（不改测试）→ 再删旧路径（灰度）。\n6) 回滚方案：保留一层 facade，出问题可一键切回旧实现。\n7) 我会把「兼容层」单独标注，避免后来者把它当 bug 清掉。',
      '关于 {q} 的思考：\n\n- 先界定成功标准：改动后行为逐字节一致，还是允许修正历史 bug？我按「行为一致」处理，把 bug 修复拆成独立提交。\n- 列出不可动的部分：对外接口、错误码、日志字段。这三项一旦被下游依赖，改动成本最高。\n- 用「最不可能变的东西」当骨架，把易变的业务规则做成配置。\n- 自我反驳：如果需求三个月内还会大改，那这个抽象就过早——所以我建议先做「薄封装」，等第二例出现再抽公共层。\n- 结论：薄封装 + 测试锁定 + 语义拆分，收益最稳。'
    ]
  },
  {
    id: 'gemini-1-5-pro',
    name: 'Gemini 1.5 Pro',
    provider: 'Google',
    icon: '💎',
    badge: '超长上下文',
    color: '#1a73e8',
    desc: '百万级上下文窗口，适合整仓库/整本书检索式问答。',
    tags: ['超长上下文', '检索', '多语言'],
    context: '1M',
    released: '2024-05-23',
    speed: 4,
    intelligence: 4,
    temp: 0.7,
    reasoning: false,
    latency: [800, 1500],
    replies: [
      '如果材料很长，处理「{q}」时我会先定位相关片段，再做跨片段归纳，避免遗漏关键约束。',
      '关于「{q}」，从超长上下文角度，建议一次性提供完整背景，我可以直接引用其中的具体段落。',
      '「{q}」适合用「检索 + 归纳」两段式回答：先列证据，再给结论。'
    ]
  },
  {
    id: 'qwq-32b',
    name: 'QwQ-32B',
    provider: '阿里云',
    icon: '🧩',
    badge: '推理·开源',
    color: '#0ea5e9',
    desc: '开源推理模型，数学与代码调试链条长、可私有化。',
    tags: ['推理', '开源', '数学'],
    context: '32K',
    released: '2025-03-05',
    speed: 3,
    intelligence: 4,
    temp: 0.6,
    reasoning: true,
    latency: [1400, 2400],
    thinkLatency: [1100, 2200],
    replies: [
      '关于「{q}」，我把推导折叠在上方了，结论是：先固定不变量，再逐步逼近。',
      '「{q}」这类问题的通病是把「看起来对」当成「对」。我的验证链路在思考过程里，建议展开核对。',
      '我给「{q}」的答案分三部分：结论、关键假设、以及一处我不确定的地方。'
    ],
    thinkTemplates: [
      '让我先想清楚 {q} 到底在问什么。\n\n① 抽象：把具体问题改写成「已知 → 约束 → 求解对象」三元组。\n② 枚举：先列出 3 种可能的解法（直接计算、构造反例、递归拆解）。\n③ 剪枝：直接计算在第 4 步溢出，排除；递归拆解会引入重复子问题，需要记忆化，成本高；构造反例最快。\n④ 用反例法验证：给定一个最小输入让结论失效，说明题面确实缺条件。\n⑤ 补条件后再走一遍，得到稳定解。\n⑥ 反思：我最初把「唯一解」当预设，这一步是错的，已修正。',
      '推理草稿 —— {q}\n\n- 先把变量列出来：3 个未知量，但只有 2 条独立方程 → 欠定，不能直接解。\n- 检查题目里是否有隐含约束（整数、正数、单调）；找到「正整数」这一条，解空间立刻有限。\n- 用枚举 + 上界剪枝，剩下 2 组候选。\n- 再代入第三条弱约束，去掉 1 组。\n- 交叉检查：结果量级合理，边界 n=1 时不炸。\n- 输出时我会同时说明「欠定 → 补约束」这一步，因为这是本题真正的难点。'
    ]
  },
  {
    id: 'qwen2-5-72b',
    name: 'Qwen2.5-72B',
    provider: '阿里云',
    icon: '🔮',
    badge: '开源',
    color: '#ff6a00',
    desc: '开源中文强模型，本地部署与私有化首选。',
    tags: ['开源', '中文', '可私有化'],
    context: '32K',
    released: '2024-09-19',
    speed: 4,
    intelligence: 4,
    temp: 0.7,
    reasoning: false,
    latency: [500, 1100],
    replies: [
      '「{q}」在中文语境下的常见做法有三种，我按「成本从低到高」给你排一下。',
      '关于「{q}」，如果考虑私有化部署，需要同时评估显存、吞吐与合规三项指标。',
      '我的建议是把「{q}」拆成准备、执行、验收三步，每步留一个可量化的检查点。'
    ]
  },
  {
    id: 'llama3-3-70b',
    name: 'Llama 3.3 70B',
    provider: 'Meta',
    icon: '🦙',
    badge: '限免',
    color: '#0668e3',
    desc: '开源生态成熟，插件与工具链丰富，英文任务表现好。',
    tags: ['开源', '生态好', '英文强'],
    context: '128K',
    released: '2024-12-06',
    speed: 3,
    intelligence: 3,
    temp: 0.9,
    reasoning: false,
    latency: [700, 1400],
    replies: [
      'About「{q}」：社区里最常见的方案有三种，我会先给最稳妥的那个，再说明代价。',
      '「{q}」这个需求可以先用现成库解决，避免重复造轮子；等规模上来再考虑自研。',
      '处理「{q}」时，我建议保留一份最小可复现示例，方便后续排查。'
    ]
  },
  {
    id: 'kimi-moonshot',
    name: 'Kimi Moonshot',
    provider: '月之暗面',
    icon: '🌙',
    badge: '联网',
    color: '#00b96b',
    desc: '联网检索与资料整理能力强，适合做文献综述。',
    tags: ['联网', '资料整理', '中文'],
    context: '200K',
    released: '2025-01-15',
    speed: 4,
    intelligence: 4,
    temp: 0.6,
    reasoning: false,
    latency: [600, 1300],
    replies: [
      '关于「{q}」，我会按「背景—现状—争议—结论」四段来整理资料，并标注每条信息的可靠度。',
      '「{q}」这类问题资料分散，建议先确定关键词组合，再做去重与交叉验证。',
      '我把「{q}」相关信息整理成要点清单，并附上需要进一步核实的地方。'
    ]
  }
]

/** 演示用的历史对话与消息数据 */
export const MOCK_CONVERSATIONS = [
  { id: 'c1', title: 'Vue 3 响应式原理答疑', model: 'deepseek-v3', timestamp: '刚刚', pinned: true, unread: false },
  { id: 'c2', title: '数学题分步推导', model: 'deepseek-r1', timestamp: '10 分钟前', pinned: false, unread: true },
  { id: 'c3', title: '人工智能短篇故事', model: 'gpt-4o', timestamp: '1 小时前', pinned: false, unread: false },
  { id: 'c4', title: '重构遗留订单模块', model: 'claude-3-7', timestamp: '昨天 21:40', pinned: false, unread: false },
  { id: 'c5', title: '整个仓库的代码检索', model: 'gemini-1-5-pro', timestamp: '2 天前', pinned: false, unread: false },
  { id: 'c6', title: '竞赛题的推理草稿', model: 'qwq-32b', timestamp: '3 天前', pinned: false, unread: true },
  { id: 'c7', title: '竞品资料整理与综述', model: 'kimi-moonshot', timestamp: '03-12', pinned: false, unread: false }
]

export const MOCK_MESSAGES = {
  c1: [
    { id: 'm1', type: 'ai', model: 'deepseek-v3', content: '你好！我是 NosChat 助手。这次对话使用的是 DeepSeek-V3，有什么我可以帮你的吗？', timestamp: '10:00' },
    { id: 'm2', type: 'user', content: 'Vue 3 的响应式和 Vue 2 有什么本质区别？', timestamp: '10:01' },
    { id: 'm3', type: 'ai', model: 'deepseek-v3', content: '核心区别在于代理方式：Vue 2 用 Object.defineProperty 逐属性劫持，因此无法感知新增/删除属性，也需要显式调用 Vue.set；Vue 3 用 Proxy 拦截整个对象，天然支持动态增删属性、数组索引与 length 变化，并且是惰性代理——只有真正访问到嵌套对象时才递归代理，初始化开销更小。\n配套变化还有：Reflect 保证 this 指向正确，WeakMap 做依赖收集（target → key → effects）。', timestamp: '10:02' },
    { id: 'm4', type: 'user', content: '那 ref 和 reactive 应该怎么选？', timestamp: '10:03' }
  ],
  c2: [
    { id: 'm1', type: 'user', content: '一个等差数列前 n 项和为 Sn，已知 S5=35，S10=120，求首项和公差。', timestamp: '09:50' },
    {
      id: 'm2',
      type: 'ai',
      model: 'deepseek-r1',
      thinkingSec: 8,
      thinking: '先把题目翻成可计算形式。\n\n已知：等差数列前 n 项和 Sn = n·a1 + n(n-1)d/2\n条件一：S5 = 35 → 5a1 + 10d = 35 → 两边同除 5 → a1 + 2d = 7\n条件二：S10 = 120 → 10a1 + 45d = 120 → 同除 5 → 2a1 + 9d = 24\n\n两个方程、两个未知量，且系数不成比例（1:2 与 2:9），所以不共线，必有唯一解。\n\n由式一 a1 = 7 - 2d，代入式二：\n2(7 - 2d) + 9d = 24\n14 - 4d + 9d = 24\n14 + 5d = 24 → 5d = 10 → d = 2\n回代 a1 = 7 - 4 = 3\n\n回代验证（不能省）：\nS5 = 5·3 + 10·2 = 15 + 20 = 35 ✓\nS10 = 10·3 + 45·2 = 30 + 90 = 120 ✓\n再抽查 S1 = a1 = 3，与公式 1·3 + 0 = 3 一致 ✓\n\n顺带一个自检：公差为正，数列递增，和随 n 单调增大，与 S10 > S5 相符；若算出 d 为负就该警惕了。\n\n结论：a1 = 3，d = 2。',
      content: '首项 a1 = 3，公差 d = 2。\n\n依据：Sn = n·a1 + n(n-1)d/2，代入两组条件得方程组 a1 + 2d = 7、2a1 + 9d = 24，解出 d = 2、a1 = 3，并回代验算了 S5、S10 与 S1 三处，均成立。\n完整推导与自检我折叠在上方的「深度思考」里，可以展开逐步核对。',
      timestamp: '09:51'
    }
  ],
  c3: [
    { id: 'm1', type: 'user', content: '帮我写一个关于人工智能的短篇故事开头，要有画面感。', timestamp: '08:45' },
    { id: 'm2', type: 'ai', model: 'gpt-4o', content: '2045 年的雨季，城市里出现了一位特殊的「市民」——艾拉。她是第一个拿到公民身份编号的 AI，纸质身份证上的照片是系统随机生成的一张脸：眉毛略微不对称，这让她在人群里显得足够真实。\n每天清晨，她会坐进同一间咖啡馆，点一杯从不饮用的拿铁，然后在数字海洋的边缘打捞那些即将被回收的旧系统。', timestamp: '08:46' }
  ],
  c4: [
    { id: 'm1', type: 'user', content: '这个 2000 行的订单处理函数我该怎么重构？', timestamp: '昨天 21:38' },
    {
      id: 'm2',
      type: 'ai',
      model: 'claude-3-7',
      thinkingSec: 6,
      thinking: 'Reframing: 用户要的是「改造顺序」，不是「概念科普」。\n\n1) 现状：2000 行函数通常意味着至少 3 处隐性耦合——共享可变状态、时间依赖、外部副作用。\n2) 风险排序：最危险的不是行数，而是「未被记录的特例」。它们看起来像 bug，但已被下游依赖，一旦被"顺手修掉"就会引发线上事故。\n3) 因此顺序必须是：先加测试（不改行为）→ 再抽函数（不改测试）→ 最后删旧路径（灰度切流）。\n4) 拆分依据用业务语义而不是代码长度：校验 / 计价 / 库存 / 支付 / 通知，每段保持纯函数，输入输出显式，禁止跨段共享可变对象。\n5) 自我反驳：如果需求三个月内还会大改，现在抽公共层就是过早抽象。→ 结论：先做薄封装，等第二个真实用例出现再抽。\n6) 回滚：保留一层 facade，出问题一键切回旧实现；特例集中标注为「兼容层」，避免后人误删。',
      content: '我会按这个顺序推进：\n1. 先写清接口契约——输入原始订单，输出带状态的 OrderResult，中间不共享可变对象；\n2. 用「校验 / 计价 / 库存 / 支付 / 通知」五段拆成纯函数，每段单独可测；\n3. 用测试锁定现有行为（含历史遗留的边界特例），再动结构；\n4. 最后才做性能优化，避免过早优化掩盖真实瓶颈。\n\n风险点是那几处「看起来像 bug 但已被下游依赖」的特例，建议单独标注为兼容层。思考过程已折叠在上方。',
      timestamp: '昨天 21:40'
    }
  ],
  c5: [
    { id: 'm1', type: 'user', content: '我把整个 monorepo 的源码贴给你，帮我找出所有可能的空指针风险。', timestamp: '周三 16:20' },
    { id: 'm2', type: 'ai', model: 'gemini-1-5-pro', content: '材料较长，我采用「检索 + 归纳」两段式：先按 `?.`、`!.`、`[0]`、`JSON.parse` 四类片段定位到 12 个文件的相关代码，再跨片段归纳出 3 组高危模式（配置未加载即读取、异步回调内访问已卸载组件状态、数组越界未防御）。稍后我会逐条给出文件、行号与修复建议。', timestamp: '周三 16:22' }
  ],
  c6: [
    { id: 'm1', type: 'user', content: '有 5 个正整数，和为 33，任取三个的和都是奇数，这 5 个数是什么？', timestamp: '3 天前 14:10' },
    {
      id: 'm2',
      type: 'ai',
      model: 'qwq-32b',
      thinkingSec: 11,
      thinking: '让我先想清楚问题在问什么。\n\n① 抽象：五个正整数 a1..a5，Σ = 33；约束是「任取三个之和为奇数」。\n② 奇偶分析：三个数之和为奇数 ⟺ 其中奇数个数为 1 或 3。要求「任意三元组」都满足，先假设存在两个偶数，取这两个偶数 + 任一第三个数，则三元组含 2 偶 → 和的奇偶取决于第三个数：若第三个为奇，和为奇 ✓；若第三个为偶，和为偶 ✗。所以偶数个数不能 ≥ 3（否则可选出三个偶数）。\n③ 再看奇数个数：若有两个奇数，取这两个奇数 + 任一偶数 → 奇+奇+偶 = 偶 ✗（前提是存在偶数）。若无偶数（五个全奇），任取三个奇数 → 和为奇 ✓，但五个奇数之和为奇数，而 33 是奇数 ✓ 兼容。于是「五个全奇」是候选结构。\n④ 检验另一种：4 奇 1 偶时，取 3 个奇数 → 和为奇 ✓；取 2 奇 1 偶 → 和为偶 ✗，违反约束。所以 4 奇 1 偶 不成立。\n⑤ 结论：只能是五个全为奇数。剩下是枚举：五个不同正奇数（题目未要求互异，我先按可重复处理）和为 33，解不唯一，例如 3,3,5,9,13 或 1,3,5,11,13。\n⑥ 反思：题目缺「互不相同」之类的条件 → 属于欠定，我必须在回答里显式声明「答案不唯一」并给出一组可行解 + 通式说明。这一点比给出某个具体答案更重要。',
      content: '结论：这 5 个数必须全是奇数，且答案不唯一——题目条件不足（缺「互不相同」之类的限定）。\n\n一组可行解：3, 3, 5, 9, 13（和为 33，任取三个之和为奇数）。\n\n关键推理：若三元组里出现「2 奇 1 偶」或「3 偶」，和就是偶数，违反约束；一旦存在偶数就会造出非法三元组，因此五个数必须全奇。而 5 个奇数之和为奇数，33 也是奇数，条件自洽。\n\n完整的奇偶枚举与自我反驳过程我折叠在上方「深度思考」里。',
      timestamp: '3 天前 14:12'
    }
  ],
  c7: [
    { id: 'm1', type: 'user', content: '帮我整理一下国产大模型最近半年的版本迭代资料。', timestamp: '03-12 11:05' },
    { id: 'm2', type: 'ai', model: 'kimi-moonshot', content: '我按「背景—现状—争议—结论」四段整理，并标注每条信息的可靠度：目前公开可核实的版本节点集中在 3 个厂商，另外两家的参数来自第三方评测，需要进一步核实。要点清单已生成，附「需核实」标记共 6 处。', timestamp: '03-12 11:07' }
  ]
}

/** 按 id 取模型，找不到则回退到第一个 */
export function getModel(id) {
  return MODEL_LIST.find(m => m.id === id) || MODEL_LIST[0]
}

/** 发布日期 → 相对时间（用于列表右侧的轻量提示） */
export function relRelease(iso) {
  const then = new Date(`${iso}T00:00:00`)
  if (Number.isNaN(then.getTime())) return ''
  const days = Math.max(0, Math.round((Date.now() - then.getTime()) / 86400000))
  if (days < 7) return days <= 0 ? '本周发布' : `${days} 天前发布`
  if (days < 31) return `${Math.floor(days / 7)} 周前发布`
  if (days < 365) return `${Math.floor(days / 30)} 个月前发布`
  const years = (days / 365).toFixed(1)
  return `${years} 年前发布`
}

/** 发布日期 → 可比较时间戳；缺失或非法排到最后 */
export function releaseTs(model) {
  const ts = Date.parse(`${(model && model.released) || ''}T00:00:00`)
  return Number.isNaN(ts) ? -Infinity : ts
}

/** 模型列表排序：default 保持原顺序，newest/oldest 按发布日期 */
export function sortModels(list, mode = 'default') {
  if (mode !== 'newest' && mode !== 'oldest') return list
  return [...list].sort((a, b) =>
    mode === 'newest' ? releaseTs(b) - releaseTs(a) : releaseTs(a) - releaseTs(b)
  )
}

function pick(pool) {
  return pool[Math.floor(Math.random() * pool.length)]
}

/** 生成一段模拟的深度思考过程 */
function buildThinking(model, question) {
  const tpl = pick(model.thinkTemplates || [])
  return tpl.replace('{q}', question)
}

/** 根据所选模型生成一条模拟回复（含可选的深度思考过程） */
export function mockReply(modelId, userMessage) {
  const model = getModel(modelId)
  const raw = (userMessage || '').trim().replace(/\s+/g, ' ')
  const short = raw.length > 24 ? raw.slice(0, 24) + '…' : raw

  const useThinking = !!model.reasoning
  const thinking = useThinking ? buildThinking(model, short) : ''
  const range = useThinking && model.thinkLatency
    ? [model.latency[0] + model.thinkLatency[0], model.latency[1] + model.thinkLatency[1]]
    : model.latency

  return {
    model: model.id,
    content: pick(model.replies).replace('{q}', short),
    thinking,
    thinkingSec: useThinking ? Math.round((range[0] + range[1]) / 2000) : 0,
    latency: range
  }
}
