package cn.edu.cjlu.taskmanagement.service.assignment;

/**
 * LLM 推荐链路不可用或调用失败时抛出，由调度层捕获并回退到备用链路。
 */
public class LlmRouteException extends RuntimeException {

    public LlmRouteException(String message) {
        super(message);
    }

    public LlmRouteException(String message, Throwable cause) {
        super(message, cause);
    }
}
