package cn.edu.cjlu.taskmanagement.service.impl;

import cn.edu.cjlu.taskmanagement.common.PageResult;
import cn.edu.cjlu.taskmanagement.common.exception.BusinessException;
import cn.edu.cjlu.taskmanagement.dto.UserQuery;
import cn.edu.cjlu.taskmanagement.dto.UserRegisterRequest;
import cn.edu.cjlu.taskmanagement.entity.User;
import cn.edu.cjlu.taskmanagement.entity.UserRole;
import cn.edu.cjlu.taskmanagement.mapper.UserMapper;
import cn.edu.cjlu.taskmanagement.vo.UserVO;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Service 层单元测试：用 Mockito 模拟 Mapper，不需要数据库。
 */
@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserMapper userMapper;

    @InjectMocks
    private UserServiceImpl userService;

    @Test
    @DisplayName("注册：默认角色 EMPLOYEE，密码 BCrypt 加密，技能标签转小写去重")
    void registerShouldApplyDefaultsAndEncodePassword() {
        when(userMapper.selectByUsername("zhangsan")).thenReturn(null);
        doAnswer(invocation -> {
            User user = invocation.getArgument(0);
            user.setId(1L);
            return 1;
        }).when(userMapper).insert(any(User.class));
        when(userMapper.selectSkillNamesByUserId(1L)).thenReturn(List.of("java", "python"));

        UserRegisterRequest request = new UserRegisterRequest();
        request.setUsername("zhangsan");
        request.setPassword("secret123");
        request.setSkills(List.of("Java", "PYTHON", " java "));

        UserVO vo = userService.register(request);

        assertThat(vo.getId()).isEqualTo(1L);
        assertThat(vo.getUsername()).isEqualTo("zhangsan");
        assertThat(vo.getRole()).isEqualTo(UserRole.EMPLOYEE.name());
        assertThat(vo.getRoleLabel()).isEqualTo("雇员");
        assertThat(vo.getSkills()).containsExactly("java", "python");
        assertThat(vo.getNickname()).isEqualTo("zhangsan");

        ArgumentCaptor<User> captor = ArgumentCaptor.forClass(User.class);
        verify(userMapper).insert(captor.capture());
        User saved = captor.getValue();
        // 密码必须以 BCrypt 摘要落库，不能是明文
        assertThat(saved.getPassword()).isNotEqualTo("secret123");
        assertThat(new BCryptPasswordEncoder().matches("secret123", saved.getPassword())).isTrue();
        verify(userMapper).insertSkills(eq(1L), anyList());
    }

    @Test
    @DisplayName("注册：用户名已存在时抛 409 业务异常，且不写入")
    void registerShouldRejectDuplicateUsername() {
        when(userMapper.selectByUsername("zhangsan")).thenReturn(new User());

        UserRegisterRequest request = new UserRegisterRequest();
        request.setUsername("zhangsan");
        request.setPassword("secret123");

        assertThatThrownBy(() -> userService.register(request))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户名已存在")
                .hasFieldOrPropertyWithValue("code", 409);
        verify(userMapper, never()).insert(any(User.class));
    }

    @Test
    @DisplayName("登录：密码正确返回用户信息")
    void loginShouldReturnUserWhenPasswordMatches() {
        User stored = new User();
        stored.setId(2L);
        stored.setUsername("lisi");
        stored.setPassword(new BCryptPasswordEncoder().encode("secret123"));
        stored.setRole(UserRole.BOSS);
        when(userMapper.selectByUsername("lisi")).thenReturn(stored);
        when(userMapper.selectSkillNamesByUserId(2L)).thenReturn(List.of());

        UserVO vo = userService.login("lisi", "secret123");

        assertThat(vo.getId()).isEqualTo(2L);
        assertThat(vo.getRole()).isEqualTo(UserRole.BOSS.name());
        assertThat(vo.getRoleLabel()).isEqualTo("老板");
    }

    @Test
    @DisplayName("登录：用户不存在或密码错误时统一抛 401，不暴露用户是否存在")
    void loginShouldThrow401WithoutRevealingExistence() {
        when(userMapper.selectByUsername(anyString())).thenReturn(null);

        assertThatThrownBy(() -> userService.login("ghost", "whatever"))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户名或密码错误")
                .hasFieldOrPropertyWithValue("code", 401);
    }

    @Test
    @DisplayName("分页查询：带技能过滤时条件转小写，size 超限被钳制为 100")
    void pageShouldNormalizeSkillAndClampSize() {
        UserQuery query = new UserQuery();
        query.setSkill("JAVA");
        query.setSize(1000);
        when(userMapper.countByQuery(any(UserQuery.class))).thenReturn(0L);

        PageResult<UserVO> result = userService.page(query);

        assertThat(result.getSize()).isEqualTo(100);
        assertThat(query.getSkill()).isEqualTo("java");
    }

    @Test
    @DisplayName("更新技能：先清空再写入，全量覆盖")
    void updateSkillsShouldReplaceAll() {
        when(userMapper.selectById(1L)).thenReturn(new User());

        userService.updateSkills(1L, List.of("Python", " C++ "));

        verify(userMapper).deleteSkillsByUserId(1L);
        verify(userMapper).insertSkills(eq(1L), eq(List.of("python", "c++")));
    }

    @Test
    @DisplayName("查询不存在的用户：抛 404 业务异常")
    void getByIdShouldThrowWhenMissing() {
        when(userMapper.selectById(99L)).thenReturn(null);

        assertThatThrownBy(() -> userService.getById(99L))
                .isInstanceOf(BusinessException.class)
                .hasMessageContaining("用户不存在")
                .hasFieldOrPropertyWithValue("code", 404);
        verify(userMapper, never()).selectSkillNamesByUserId(anyLong());
    }
}
