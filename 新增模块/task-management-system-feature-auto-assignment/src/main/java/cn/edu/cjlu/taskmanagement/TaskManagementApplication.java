package cn.edu.cjlu.taskmanagement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 任务管理系统启动类。
 *
 * <p>分层结构：controller（接口层）→ service（业务层）→ mapper（持久层）→ MySQL，
 * 实体 entity / 请求 DTO / 响应 VO 分别负责三层之间的数据传递。</p>
 */
@SpringBootApplication
public class TaskManagementApplication {

    public static void main(String[] args) {
        SpringApplication.run(TaskManagementApplication.class, args);
    }
}
