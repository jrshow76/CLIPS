package com.shelfy.subscription.repository;

import com.shelfy.subscription.entity.SubscriptionPayment;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SubscriptionPaymentRepository extends JpaRepository<SubscriptionPayment, Long> {
}
