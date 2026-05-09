package com.shelfy.config;

import com.shelfy.item.mapper.StringArrayTypeHandler;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.mybatis.spring.SqlSessionFactoryBean;

import javax.sql.DataSource;

/**
 * MyBatis 설정
 * <p>
 * TypeHandler 등록:
 * - StringArrayTypeHandler: PostgreSQL VARCHAR[] ↔ List<String>
 */
@Configuration
@MapperScan("com.shelfy.*.mapper")
public class MyBatisConfig {

    /**
     * application.yml의 mybatis 설정과 함께 동작.
     * TypeHandler는 mapper XML의 typeHandler 속성 또는 자동 감지로 등록.
     */
    @Bean
    public StringArrayTypeHandler stringArrayTypeHandler() {
        return new StringArrayTypeHandler();
    }
}
