package cn.edu.cjlu.taskmanagement.service.assignment;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * LLM 备用链路配置项，对应 application.yml 的 {@code llm.*}。
 *
 * <p>按 OpenAI 兼容协议设计，换厂商只需改配置，代码不动：</p>
 * <ul>
 *   <li>DeepSeek：base-url=https://api.deepseek.com，model=deepseek-chat</li>
 *   <li>智谱 GLM：base-url=https://open.bigmodel.cn/api/paas/v4，model=glm-4-flash，
 *       chat-path=/chat/completions</li>
 *   <li>OpenAI：base-url=https://api.openai.com，model=gpt-4o-mini</li>
 * </ul>
 * api-key 一律通过环境变量注入，不要写进仓库。
 */
@Data
@Component
@ConfigurationProperties(prefix = "llm")
public class LlmProperties {

    /** OpenAI 兼容服务根地址，例如 https://api.deepseek.com */
    private String baseUrl = "";

    /** 对话接口路径，拼在 base-url 后面；不同厂商的路径前缀不同 */
    private String chatPath = "/v1/chat/completions";

    /** API Key，建议用环境变量 LLM_API_KEY 注入 */
    private String apiKey = "";

    /** 模型名，例如 deepseek-chat / glm-4-flash / gpt-4o-mini */
    private String model = "";

    /** 读超时秒数（连接超时固定 10 秒） */
    private int timeoutSeconds = 20;

    /** 送入提示词的最大候选人数，防止任务过多时提示词膨胀 */
    private int maxCandidates = 20;

    /** 三项关键配置齐了才算可用 */
    public boolean isConfigured() {
        return notBlank(baseUrl) && notBlank(apiKey) && notBlank(model);
    }

    private static boolean notBlank(String value) {
        return value != null && !value.isBlank();
    }
}
