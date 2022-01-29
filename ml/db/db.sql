CREATE DATABASE zakolko CHARACTER SET='utf8'; 

CREATE TABLE `inzeraty` (
        `id` VARCHAR(255),
        `zdroj` VARCHAR(255),
        `ulica` VARCHAR(255),
        `mesto` VARCHAR(255),
        `okres` VARCHAR(255),
        `druh` VARCHAR(255),
        `stav` VARCHAR(255),
        `kurenie` VARCHAR(255),
        `energ_cert` VARCHAR(255),
        `orientacia` VARCHAR(255),
        `telkoint` VARCHAR(255),
        `uzit_plocha` FLOAT,
        `cena_m2` FLOAT,
        `cena` FLOAT,
        `rok_vystavby` INT,
        `pocet_nadz_podlazi` TINYINT,
        `pocet_izieb` TINYINT,
        `podlazie` TINYINT,
        `latitude` DOUBLE,
        `longitude` DOUBLE,
        `verejne_parkovanie` VARCHAR(100),
        `vytah` VARCHAR(100),
        `lodzia` VARCHAR(100),
        `balkon` VARCHAR(100),
        `garazove_statie` VARCHAR(100),
        `garaz` VARCHAR(100),
        `timestamp` timestamp,
        PRIMARY KEY (`zdroj`,`id`)
) ENGINE=InnoDB CHARSET='utf8';

CREATE USER 'scraper'@'localhost' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON *.* TO 'scraper'@localhost IDENTIFIED BY 'password';
