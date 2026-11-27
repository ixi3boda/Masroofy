package com.example.finance.update;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

/** Runs the updates at 09:00, 15:00 and 21:00 Cairo time (see app.update.* in application.properties). */
@Component
public class UpdateJob {
    private final UpdateService updates;
    private final boolean onStartup;

    public UpdateJob(UpdateService updates, @Value("${app.update.on-startup}") boolean onStartup) {
        this.updates = updates;
        this.onStartup = onStartup;
    }

    @Scheduled(cron = "${app.update.cron}", zone = "${app.update.zone}")
    public void scheduled() {
        updates.updateAll();
    }

    @EventListener(ApplicationReadyEvent.class)
    public void atStartup() {
        if (onStartup) {
            // In its own thread so the API is up while the first update runs.
            Thread.ofVirtual().name("startup-update").start(updates::updateAll);
        }
    }
}
