package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.UserQuery;
import cn.edu.cjlu.taskmanagement.dto.UserRegisterRequest;
import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import cn.edu.cjlu.taskmanagement.service.UserService;
import cn.edu.cjlu.taskmanagement.vo.UserVO;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * 用户业务实现。
 *
 * <p>职责：用户名唯一性校验、BCrypt 密码加密与校验、技能标签规范化
 * （转小写、去重、去空白）、组装 VO。登录失败不区分"用户不存在"和"密码错误"。</p>
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class UserServiceImpl implements UserService {

    /** 单例复用：BCryptPasswordEncoder 线程安全 */
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    private final UserMapper userMapper;

    @Override
    @Transactional
    public UserVO register(UserRegisterRequest request) {
        String username = request.getUsername().trim();
        if (userMapper.selectByUsername(username) != null) {
            throw new BusinessException(409, "用户名已存在：" + username);
        }

        LocalDateTime now = LocalDateTime.now();
        User user = new User();
        user.setUsername(username);
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setNickname(request.getNickname() == null || request.getNickname().isBlank()
                ? username : request.getNickname().trim());
        user.setRole(request.getRole() == null ? UserRole.EMPLOYEE : request.getRole());
        user.setCreatedAt(now);
        user.setUpdatedAt(now);

        userMapper.insert(user);
        saveSkills(user.getId(), request.getSkills());
        log.info("新用户注册：id={}, username={}, role={}", user.getId(), username, user.getRole());
        return UserVO.from(user, loadSkills(user.getId()));
    }

    @Override
    public UserVO login(String username, String password) {
        User user = userMapper.selectByUsername(username == null ? "" : username.trim());
        // 统一提示，不暴露"用户是否存在"
        if (user == null || !passwordEncoder.matches(password, user.getPassword())) {
            throw new BusinessException(401, "用户名或密码错误");
        }
        return UserVO.from(user, loadSkills(user.getId()));
    }

    @Override
    public PageResult<UserVO> page(UserQuery query) {
        UserQuery condition = query == null ? new UserQuery() : query;
        int page = Math.max(condition.getPage(), 1);
        int size = Math.min(Math.max(condition.getSize(), 1), 100);
        int offset = (page - 1) * size;
        condition.setPage(page);
        condition.setSize(size);
        if (condition.getSkill() != null) {
            condition.setSkill(normalizeSkill(condition.getSkill()));
        }

        long total = userMapper.countByQuery(condition);
        if (total == 0) {
            return PageResult.of(List.of(), 0L, page, size);
        }

        List<UserVO> records = userMapper.selectPage(condition, offset, size)
                .stream()
                .map(user -> UserVO.from(user, loadSkills(user.getId())))
                .toList();
        return PageResult.of(records, total, page, size);
    }

    @Override
    public UserVO getById(Long id) {
        return UserVO.from(requireUser(id), loadSkills(id));
    }

    @Override
    @Transactional
    public void updateSkills(Long userId, List<String> skills) {
        requireUser(userId);
        userMapper.deleteSkillsByUserId(userId);
        saveSkills(userId, skills);
    }

    /** 查找用户，不存在直接抛 404 */
    private User requireUser(Long id) {
        if (id == null) {
            throw new BusinessException("用户 ID 不能为空");
        }
        User user = userMapper.selectById(id);
        if (user == null) {
            throw new BusinessException(404, "用户不存在：" + id);
        }
        return user;
    }

    /** 规范化并落库技能标签；空列表等价于清空 */
    private void saveSkills(Long userId, List<String> skills) {
        if (skills == null || skills.isEmpty()) {
            return;
        }
        Set<String> normalized = new LinkedHashSet<>();
        for (String skill : skills) {
            String value = normalizeSkill(skill);
            if (!value.isEmpty()) {
                normalized.add(value);
            }
        }
        if (!normalized.isEmpty()) {
            userMapper.insertSkills(userId, List.copyOf(normalized));
        }
    }

    /** 技能标签统一转小写并去首尾空白，便于与任务的所需技能精确匹配 */
    private String normalizeSkill(String skill) {
        return skill == null ? "" : skill.trim().toLowerCase(Locale.ROOT);
    }

    private List<String> loadSkills(Long userId) {
        return userMapper.selectSkillNamesByUserId(userId);
    }
}
