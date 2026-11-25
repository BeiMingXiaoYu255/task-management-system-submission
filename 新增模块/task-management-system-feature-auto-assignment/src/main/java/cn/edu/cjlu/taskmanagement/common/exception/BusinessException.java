package cn.edu.cjlu.taskmanagement.common.exception;

/**
 * 业务异常：由 service 层抛出，交给 {@link GlobalExceptionHandler} 转成统一响应。
 *
 * <p>code 约定与 HTTP 状态码对齐：400 参数/业务校验失败，404 资源不存在，409 冲突等。</p>
 */
public class BusinessException extends RuntimeException {

    private final int code;

    public BusinessException(String message) {
        this(400, message);
    }

    public BusinessException(int code, String message) {
        super(message);
        this.code = code;
    }

    public int getCode() {
        return code;
    }
}
