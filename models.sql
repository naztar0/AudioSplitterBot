create table users
(
    id         int unsigned auto_increment
        primary key,
    user_id    bigint unsigned                       not null,
    locale     varchar(8)                            not null,
    created_at timestamp default current_timestamp() not null
)
    charset = latin1;

create table audiofiles
(
    id         int unsigned auto_increment
        primary key,
    user_id    int unsigned                                                                       not null,
    title      varchar(256) charset utf8mb4                                                       not null,
    stem       varchar(16)                                                                        not null,
    level      tinyint(1)                                                                         not null,
    status     enum ('init', 'await', 'error', 'complete', 'cleared') default 'init'              not null,
    created_at timestamp                                              default current_timestamp() not null,
    constraint audiofile_fk
        foreign key (user_id) references users (id)
            on update cascade on delete cascade
)
    charset = latin1;
