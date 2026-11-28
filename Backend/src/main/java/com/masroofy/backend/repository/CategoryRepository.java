package com.masroofy.backend.repository;

import com.masroofy.backend.model.Category;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

/** Categories a user can see: the system defaults (user_id NULL) and their own, never hidden ones. */
@Repository
public class CategoryRepository {

    private static final String COLUMNS = "id, user_id, name, kind, icon, is_hidden";
    private static final String VISIBLE_TO_USER = "(user_id IS NULL OR user_id = ?) AND NOT is_hidden";

    private static final RowMapper<Category> ROW_MAPPER = (rs, rowNum) -> new Category(
            rs.getObject("id", UUID.class),
            rs.getObject("user_id", UUID.class),
            rs.getString("name"),
            rs.getString("kind"),
            rs.getString("icon"),
            rs.getBoolean("is_hidden"));

    private final JdbcTemplate jdbcTemplate;

    public CategoryRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * System defaults first, in seed order (expense keys, then income keys), then the user's own by name.
     *
     * @param kind {@code expense}, {@code income}, or null for both
     */
    public List<Category> findVisible(UUID userId, String kind) {
        String sql = "SELECT " + COLUMNS + " FROM categories WHERE " + VISIBLE_TO_USER
                + (kind == null ? "" : " AND kind = ?")
                + " ORDER BY user_id NULLS FIRST, CASE WHEN user_id IS NULL THEN id END, name";
        return kind == null
                ? jdbcTemplate.query(sql, ROW_MAPPER, userId)
                : jdbcTemplate.query(sql, ROW_MAPPER, userId, kind);
    }

    /** By the app's category key; a system default wins over a user category with the same key. */
    public Optional<Category> findVisibleByKey(UUID userId, String key) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM categories WHERE icon = ? AND " + VISIBLE_TO_USER
                + " ORDER BY user_id NULLS FIRST LIMIT 1", ROW_MAPPER, key, userId).stream().findFirst();
    }

    public Optional<Category> findVisibleById(UUID userId, UUID id) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM categories WHERE id = ? AND " + VISIBLE_TO_USER,
                ROW_MAPPER, id, userId).stream().findFirst();
    }
}
