package cn.edu.cjlu.taskmanagement.dto;

import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.List;

/**
 * 更新用户技能标签的请求参数。
 *
 * <p>全量覆盖：以本次提交的列表为准。</p>
 */
@Data
public class UserUpdateSkillsRequest {

    @Size(max = 20, message = "技能标签最多 20 个")
    private List<String> skills;
}
