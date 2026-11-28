package com.masroofy.transaction;

import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Stores a short list of field names as "amount,category" in one column. */
@Converter
public class StringListConverter implements AttributeConverter<List<String>, String> {

    @Override
    public String convertToDatabaseColumn(List<String> values) {
        return values == null ? "" : String.join(",", values);
    }

    @Override
    public List<String> convertToEntityAttribute(String column) {
        if (column == null || column.isBlank()) {
            return new ArrayList<>();
        }
        return new ArrayList<>(Arrays.asList(column.split(",")));
    }
}
