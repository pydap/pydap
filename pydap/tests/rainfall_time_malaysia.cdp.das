Attributes {
    NC_GLOBAL {
        Int32 max_profiles_per_request 5000;
        Int32 total_profiles_in_dataset 33;
        String version "1.1.0";
        String owner "";
        String contact "";
        String Conventions "epic-insitu-1.0";
        Float64 lon_range 99.7300033569336, 118.069999694824;
        Float64 lat_range 1.22000002861023, 6.92000007629395;
        Float64 depth_range 0.0, 0.0;
        Float64 time_range -5.995728E11, 8.835696E11;
    }
    location._id {
        String long_name "sequence id";
        Int32 missing_value 2147483647;
        String units "";
    }
    location.lon {
        String units "degree_east";
        String long_name "LONGITUDE                ";
        Float32 missing_value NaN;
        String axis "X";
    }
    location.time_series.time {
        String units "msec since 1970-01-01 00:00:00 GMT";
        String long_name "time";
        Float64 missing_value NaN;
        String axis "T";
    }
    location.lat {
        String units "degree_north";
        String long_name "LATITUDE                 ";
        Float32 missing_value NaN;
        String axis "Y";
    }
    location.depth {
        String units "m";
        String long_name "DEPTH (M)                ";
        Float32 missing_value NaN;
        String axis "Z";
    }
    location.time_series.Rn_963 {
        String units "mm";
        String long_name "rainfall                 ";
        Float32 missing_value NaN;
    }
}
