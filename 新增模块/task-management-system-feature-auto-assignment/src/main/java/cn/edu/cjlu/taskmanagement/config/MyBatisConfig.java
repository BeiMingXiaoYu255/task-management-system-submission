package cn.edu.cjlu.taskmanagement.config;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;

/**
 * MyBatis 配置：扫描 Mapper 接口。
 *
 * <p>单独放在配置类里（而不是启动类上），这样 {@code @WebMvcTest} 等切片测试
 * 不会因为加载启动类而被迫初始化数据源。</p>
 */
@Configuration
@MapperScan("cn.edu.cjlu.taskmanagement.mapper")
public class MyBatisConfig {
}
