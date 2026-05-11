package com.tulip.tenant.config;

import com.tulip.common.data.handler.JsonbTypeHandler;
import com.tulip.tenant.outbox.RlsSessionApplier;
import org.apache.ibatis.session.SqlSessionFactory;
import org.mybatis.spring.boot.autoconfigure.ConfigurationCustomizer;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.core.ProducerFactory;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * tenant-service 인프라(MyBatis + Kafka + Tx + RLS) 빈 설정.
 */
@Configuration
public class TenantInfraConfig {

    /** MyBatis 글로벌 설정 — TypeHandler 및 Interceptor 등록. */
    @Bean
    public ConfigurationCustomizer myBatisConfigurationCustomizer(
            ObjectProvider<RlsSessionApplier> rlsApplierProvider) {
        return cfg -> {
            cfg.getTypeHandlerRegistry().register(JsonbTypeHandler.class);
            cfg.addInterceptor(new RlsMyBatisInterceptor(rlsApplierProvider));
        };
    }

    @Bean
    public KafkaTemplate<String, String> kafkaTemplate(ProducerFactory<String, String> producerFactory) {
        return new KafkaTemplate<>(producerFactory);
    }

    /** Outbox Poller 가 사용하는 짧은 트랜잭션 템플릿. */
    @Bean
    public TransactionTemplate transactionTemplate(PlatformTransactionManager txManager) {
        return new TransactionTemplate(txManager);
    }

    /** SqlSessionFactory 로 인터셉터 적용 보장 (자동설정 + customizer 조합). */
    @Bean
    public SqlSessionFactoryFactoryPostProcessorMarker sqlSessionFactoryMarker(SqlSessionFactory factory) {
        return new SqlSessionFactoryFactoryPostProcessorMarker(factory);
    }

    /** 명시적 의존성을 표시하기 위한 마커 빈 — Spring 의 빈 생성 순서를 안내. */
    public static class SqlSessionFactoryFactoryPostProcessorMarker {
        private final SqlSessionFactory factory;
        public SqlSessionFactoryFactoryPostProcessorMarker(SqlSessionFactory factory) {
            this.factory = factory;
        }
        public SqlSessionFactory getFactory() { return factory; }
    }
}
