package cn.edu.cjlu.taskmanagement.service.assignment;

/**
 * 推荐链路调度模式，共四种可选：
 *
 * <ul>
 *   <li>{@link #LOCAL_ONLY} —— 只用本地规则引擎；</li>
 *   <li>{@link #LLM_ONLY} —— 只用大语言模型 API；</li>
 *   <li>{@link #LOCAL_FIRST} —— 优先本地，失败/无匹配时回退 LLM（默认）；</li>
 *   <li>{@link #LLM_FIRST} —— 优先 LLM，失败/无匹配时回退本地。</li>
 * </ul>
 *
 * <p>通过 {@code assignment.dispatch-mode}（环境变量 {@code ASSIGNMENT_DISPATCH_MODE}）配置。</p>
 */
public enum DispatchMode {

    LOCAL_ONLY,
    LLM_ONLY,
    LOCAL_FIRST,
    LLM_FIRST
}
